# Plan 003 — Postulación asistida (fase 1: modo `assist`)

Referencias: `docs/constitution.md` (P5, P6, P8), `spec.md`.

> La fase 1 está implementada. La fase 2 (`auto`) cerró en T6 (2026-10-06): T0–T6 hechas, criterios de finalización de la spec en verde.

## Módulos

- `src/config.py`: `apply_mode` (`off` | `assist` | `auto`, default `assist`) y `apply_daily_limit` (límite de `auto`). Cubre RF-1, RF-2, RF-9.
- `src/notifier/template.py`: bloque "Postulación asistida" por oferta en el correo: enlace de postulación, datos del perfil a usar, carta (si existe) y checklist (requisitos, nivel, ubicación, idioma, confirmar que sigue activa). Cubre RF-2.
- `src/main.py`: `effective_apply_mode()` devuelve `auto` (T5, RF-2b sin efecto) y `run_auto()` ejecuta `run_batch` con `config.apply_daily_limit`/`config.apply_paused`; si el navegador no está disponible, opera en `assist` (Decisión 2). Cubre RF-2b, RF-3, RF-4, RF-9, RF-10.

## Modelo de datos

```text
apply_mode: str       — "off" | "assist" | "auto" (env APPLY_MODE)
apply_daily_limit: int — límite diario, reservado para la fase 2 (RF-4)
```

Checklist por oferta (derivada de datos existentes, sin inventar):

1. Abrir la oferta y verificar que sigue activa.
2. Revisar que el nivel/ubicación/idioma calzan con el perfil.
3. Usar la carta generada y adaptar el saludo si la empresa tiene nombre visible.
4. Enviar con los datos del perfil (email, LinkedIn, GitHub, portfolio).
5. Registrar la fecha de envío.

## Decisiones justificadas

### Decisión 1: `assist` se materializa en el reporte, no en un módulo nuevo
- **Elegido:** checklist + carta dentro del correo existente.
- **Alternativa descartada:** módulo `src/apply/` con clases de paquete de postulación.
- **Motivo:** P8; RF-2 pide "preparar y notificar", y la notificación ya es el correo.

### Decisión 2: `auto` no implementado degrada a `assist`, no falla
- **Elegido:** log + operación en `assist`.
- **Alternativa descartada:** error que aborta el run.
- **Motivo:** RF-2b; el reporte diario no debe perderse por una configuración adelantada.
- **Extensión (T5):** el mismo principio aplica si `auto` está configurado pero Playwright/navegador no está disponible: la ejecución opera en `assist` (la variante de infraestructura de RF-2b); no se envía nada.

## Contrato público

- `Config.apply_mode: str` (nuevo).
- HTML: sección "Postulación asistida" por tarjeta cuando `apply_mode == "assist"`.

## Estrategia de tests

- **Unitarios:** `apply_mode` default `assist`; modo `auto` → log y operación `assist`; modo `off` → sin checklist.
- **Integración:** generación del HTML con checklist y carta incluidos.

## Mapeo RF → módulo → test

| RF | Módulo | Test |
|----|--------|------|
| RF-1 | `config` + `template` | `tests/test_apply_mode.py::test_off_has_no_checklist` |
| RF-2 | `template` | `tests/test_apply_mode.py::test_assist_includes_checklist_and_letter` |
| RF-2b | `main` | `tests/test_apply_mode.py::test_auto_mode_is_effective`, `::test_run_auto_falls_back_without_browser` |
| RF-3, RF-8 | `apply.runner`, `apply.ledger` | `tests/test_apply_runner.py`, `tests/test_apply_batch.py` |
| RF-4 | `apply.batch` | `tests/test_apply_batch.py` (límite) |
| RF-5 | `apply.registry` | `tests/test_apply_registry.py`, `tests/test_apply_runner.py` (`dominio_no_soportado`), `tests/test_apply_block.py::test_demoted_family_blocked` |
| RF-6 | `apply.runner` | `tests/test_apply_runner.py` |
| RF-7 | `apply.runner`, `apply.batch` | `tests/test_apply_block.py` |
| RF-9 | `config` + `apply.batch` | `tests/test_apply_batch.py` (pausa) |
| RF-10 | `main` | `tests/test_apply_mode.py::test_run_auto_executes_batch` |
| RNF-1 | `apply.runner` | `tests/test_apply_runner.py` (timeout 90 s) |
| RNF-3 | `main._open_browser` | headless por defecto (código) |
| RNF-4 | tests | fixtures locales, sin red |

---

## Fase 2 — Plan de selectores (`auto`) — T0

Decisiones aprobadas por el usuario (2026-10-06):

1. **Alcance de dominios:** piloto por *familia ATS* — solo se postula cuando la oferta cae en un ATS con formulario estable y sin login: **Greenhouse** (`boards.greenhouse.io`, `job-boards.greenhouse.io`), **Lever** (`jobs.lever.co`), **Ashby** (`jobs.ashbyhq.com`), **Workable** (`apply.workable.com`). LinkedIn queda excluido (decisión previa). Todo lo demás → `dominio_no_soportado` (RF-5).
2. **Playwright:** aprobado headless para **envío** en esas familias (extiende la aprobación de solo lectura de LinkedIn posts). 90 s por envío (RNF-1), parada ante CAPTCHA/login imprevisto (RF-7), tests solo con fixtures (RNF-4).
3. **Límite:** `APPLY_DAILY_LIMIT` (default 5) por ejecución **y** por día (RF-4); se corta al alcanzarlo.
4. **Registro:** `storage/applications.json` (P8: json simple antes que Mongo) con oferta, dominio, fecha, resultado, motivo si falló (RF-8).

### Flujo por oferta (una sola pasada, sin reintentos salvo RF-6)

1. Resolver la `apply_url` hasta el hostname final (redirect + enlace de salida en la página del tablero).
2. Si el hostname pertenece a una familia registrada **y validada** → continuar; si no → `dominio_no_soportado` (RF-5), sin intentar.
3. Navegar headless; localizar el formulario de la familia (selector registrado). Si no existe → fallo `selector_ausente` (RF-6), se marca la familia como `requiere_mantenimiento`.
4. Rellenar **solo campos con dato en `cvs/profile.json`** (name, email, linkedin, github; carta generada en cover letter). **Nunca se inventan datos (P6).** Campo obligatorio sin dato (p. ej. teléfono, archivo CV) → fallo `dato_faltante`, se lista en el reporte para que el usuario lo complete en el CV.
5. Si aparece CAPTCHA o login requerido → se detiene el modo `auto` de la sesión y se reporta (RF-7).
6. Enviar; esperar confirmación (selector de éxito o URL de agradecimiento de la familia). Tomar captura/HTML → evidencia (RF-3).
7. Registrar en `storage/applications.json` (RF-8); contar para el límite (RF-4); continuar con la siguiente oferta.

### Registro de selectores por familia (`src/apply/registry.py`, fase 2)

```text
FamilySpec(
  name, host_patterns,          # patrones de hostname
  form_selector,                # selector del formulario (validado)
  field_selectors,              # {nombre, email, linkedin, github, cover_letter}
  submit_selector,
  success_selector | success_url_pattern,
  validated: bool,              # solo validated=True postula (RF-5)
)
```

- Los selectores **no se adivinan**: se capturan en la tarea T1 con una página real (solo lectura), se guardan como fixture HTML y se prueban contra la fixture (RNF-4, RF-5).
- Si un selector falla en producción → fallo limpio (RF-6) + `validated=False` automático para esa familia.

### Limitaciones conocidas (aceptadas)

- Formularios que exigen teléfono o archivo CV fallan con `dato_faltante` hasta que el usuario amplíe `cvs/profile.json` (no se inventan datos).
- **Política CAPTCHA (aprobada 2026-10-06):** CAPTCHA interactivo visible → familia bloqueada y sesión `auto` detenida (RF-7); tokens invisibles sin interacción → se envía y un rechazo del servidor es fallo RF-6 registrado.
- Familias con protecciones Cloudflare/CAPTCHA no entran al piloto hasta decisión nueva (RF-7, P3).
- Orden de habilitación con evidencia T1 (muestreo 2026-10-06): **Greenhouse primero** (validada, 2 hits), luego Ashby (7 hits) si su CAPTCHA visible se resuelve con decisión nueva, y Lever/Workable cuando se capturen sus formularios.

### Tests de la fase 2 (T1+)

- Unitarios por familia con fixtures HTML locales: rellena campos, envía, detecta éxito; sin red (RNF-4).
- `dominio_no_soportado` y `dato_faltante` cubren RF-5 y P6.
- Límite diario: RF-4 con contador simulado.
- RF-9 (pausa) y RF-6 (fallo + un reintento) con spies.
