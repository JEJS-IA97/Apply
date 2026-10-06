# Spec 003 — Postulación asistida/automática (Playwright)

## Contexto y objetivo

El usuario propone que el bot no solo reporte, sino que **postule**. Técnicamente es posible automatizando el navegador (Playwright) y teniendo selectores por página. Esta spec define el alcance, los límites de seguridad y las decisiones de la fase 2 (resueltas el 2026-10-06; ver "Decisiones tomadas" y `plan.md`).

Nota de stack: se propone **Playwright (Python)** y no Cypress, porque Cypress está diseñado para testear la app propia, no para automatizar sitios de terceros; el proyecto ya usa Python y Playwright permite selectores multiplataforma y modo headless.

## Usuarios / actores

- **José**: quiere postular sin hacerlo a mano, pero sin arriesgar sus cuentas ni postular a basura.
- **Employer** (tercero): recibe postulaciones reales y verificables; el bot no debe generar spam.

## Historias de usuario

- H1: Como José quiero que el bot prepare la postulación (datos + carta) y la envíe solo donde sea seguro, para ahorrar tiempo sin perder control.
- H2: Como José quiero un límite diario de envíos para no parecer spam ni ser bloqueado.
- H3: Como mantenedor quiero un registro de cada envío (URL, fecha, resultado) para auditar y retomar.

## Requisitos funcionales (criterios de aceptación en EARS)

> Los RF-1 a RF-4 dependen de la decisión de modo; se redactan cubriendo los tres modos posibles.

- RF-1: CUANDO el modo de postulación está en `off`, EL SISTEMA se limita a reportar y no prepara paquete de postulación.
- RF-2: CUANDO el modo es `assist` (por defecto), EL SISTEMA prepara para cada oferta elegible la URL de postulación, los datos del perfil, la carta de presentación y una checklist de lo que falta, y notifica al usuario; **no envía** la postulación.
- RF-2b: CUANDO `APPLY_MODE=auto` y el modo `auto` no está implementado, EL SISTEMA registra `auto no implementado` y opera en `assist`; nunca envía una postulación. *(Condición histórica: T5 implementó `auto`; ver "Decisiones tomadas".)*
- RF-3: CUANDO el modo es `auto` y la oferta pertenece a un dominio con selectores registrados y aprobados, EL SISTEMA completa y envía la postulación, registrando URL, timestamp, resultado y captura/HTML de confirmación.
- RF-4: MIENTRAS el modo `auto` esté activo, EL SISTEMA respeta un límite máximo de envíos por ejecución y por día (configurable, objetivo ≤ 5/día) y se detiene al alcanzarlo.
- RF-5: SI un dominio no tiene selectores registrados o validados, ENTONCES EL SISTEMA no intenta postular y lo marca como `dominio_no_soportado` (nunca adivina selectores).
- RF-6: CUANDO la postulación falla (selector ausente, CAPTCHA, login expirado, redirección inesperada), EL SISTEMA detiene ese intento, registra el error, no reintenta más de una vez y continúa con la siguiente oferta.
- RF-7: EL SISTEMA nunca elude CAPTCHAs, verificaciones anti-bot ni controles de acceso; si los encuentra, detiene el modo `auto` para esa sesión y lo reporta (P3, P5).
- RF-8: EL SISTEMA mantiene un archivo de registro (`storage/applications.json` o MongoDB) con cada envío: oferta, dominio, fecha, resultado, motivo si falló.
- RF-9: CUANDO el usuario pausa el modo (flag/env), EL SISTEMA no envía ninguna postulación en esa ejecución.
- RF-10: EL SISTEMA solo postula a ofertas que ya pasaron los filtros de las specs 001 y 002 (nivel, confianza, idioma, remote).

## Requisitos no funcionales

- RNF-1: Un envío individual no debe tardar más de 90 s (timeout) antes de reportar fallo.
- RNF-2: Las credenciales (LinkedIn, correo) se toman solo de `.env`; nunca se escriben en código, logs ni repositorio.
- RNF-3: El navegador corre headless por defecto; el modo visible existe solo para depuración local.
- RNF-4: La suite de tests no realiza envíos reales: los selectores se prueban con páginas fixture locales.

## Casos límite

- Login expirado en medio de la ejecución → RF-6 (detiene ese intento) y pausa `auto` si ocurre en la primera oferta (posible bloqueo).
- Oferta sin `apply_url` → `dominio_no_soportado`, no intenta.
- Selectores que cambiaron en el sitio → el intento falla limpio (RF-6) y se marca el dominio como requiere mantenimiento.
- Dos ofertas del mismo dominio en una ejecución → ambas cuentan para el límite (RF-4).

## Fuera de alcance

- Eludir CAPTCHAs o restricciones anti-bot (explícitamente prohibido, RF-7).
- Postular a dominios sin selectores aprobados (RF-5).
- Generar datos de postulación que no estén en el CV del usuario (P6).
- Click-masivo/quick-apply en LinkedIn sin revisión (riesgo de baneo; requiere decisión).

## Criterios de finalización

- [x] Todos los RF tienen al menos un test que los cubre. *(Evidencia: `tasks.md` T6.)*
- [x] Todos los RNF verificables están medidos o evidenciados. *(RNF-1 test de timeout; RNF-2: hallazgo de `.env` rastreado, des-trackeado en `7685efc` — rotación de credenciales pendiente fuera del repo; RNF-3 headless por defecto; RNF-4 suite sin red.)*
- [x] Los casos límite están cubiertos. *(login a mitad, sin `apply_url`, selectores caídos, mismo dominio repetido — ver `tasks.md` T6.)*
- [x] La suite de tests pasa en verde (sin envíos reales). *(91 passed, ruff limpio, 2026-10-06.)*
- [x] No hay código sin RF que lo justifique. *(Mapeo RF→módulo→test en `plan.md`.)*

## Decisiones tomadas (2026-10-06, aprobadas por el usuario)

- **Modo:** `assist` (asistida) por defecto. El sistema prepara paquete de postulación (URL, datos del CV, carta, checklist) y notifica; **no envía**. RF-3 (`auto`) queda sin implementar hasta un plan con selectores por dominio; si `APPLY_MODE=auto` hoy, el sistema registra que no está implementado y opera en `assist` (nunca envía).
- **Playwright:** aprobado como dependencia solo para **lectura** de publicaciones de LinkedIn (RF-11 de la spec 002). No se usa para enviar postulaciones en esta fase.
- **LinkedIn:** queda excluido de cualquier modo `auto` futuro (riesgo de restricción de la cuenta); revisado en la fase de selectores.
- **Dominios para `auto`:** piloto por familia ATS aprobado (T0, 2026-10-06): Greenhouse, Lever, Ashby y Workable; el resto de dominios → `dominio_no_soportado` (RF-5). Plan de selectores aprobado en `plan.md` (sección "Fase 2").
- **Playwright para envío (T0, 2026-10-06):** aprobado headless para enviar postulaciones en las familias ATS del piloto; extiende la aprobación de solo lectura de LinkedIn posts. Con 90 s por envío, parada ante CAPTCHA (RF-7) y tests solo con fixtures (RNF-4).
- **Límite diario y registro (T0, 2026-10-06):** confirmados `APPLY_DAILY_LIMIT` (default 5, RF-4) y registro en `storage/applications.json` (RF-8, P8).
- **Política CAPTCHA para RF-7 (T1, 2026-10-06, aprobada por el usuario):** un CAPTCHA **interactivo visible** (casilla/reto) bloquea la familia y detiene el modo `auto` de la sesión; los **tokens invisibles sin interacción** (p. ej. reCAPTCHA Enterprise de Greenhouse) no son un desafío: se envía normalmente y un rechazo del servidor cuenta como fallo RF-6 registrado, sin reintento.
- **Evidencia T1 (2026-10-06):** muestreo de 190 páginas de oferta (solo lectura): familias observadas **Ashby (7)** y **Greenhouse (2)**; Lever/Workable sin volumen en la muestra. Selectores capturados en fixtures (`tests/fixtures/ats_greenhouse.html`, `ats_ashby_form.html`, este último con navegador headless porque Ashby es SPA). **Familia inicial del piloto: Greenhouse** (validada, CAPTCHA invisible). Ashby registrada y validada pero **bloqueada** por CAPTCHA visible (RF-7). Lever/Workable registradas como `pendiente_captura` (RF-5).
- **`auto` implementado (T5, 2026-10-06):** RF-2b **deja de aplicar**; `APPLY_MODE=auto` ejecuta el lote sobre los matches filtrados (RF-10) con límite (RF-4), pausa (RF-9) y registro (RF-8). Si Playwright o el navegador no están disponibles, la ejecución **opera en `assist`** (extiende Decisión 2 de `plan.md`) y el reporte conserva la checklist; no se envía nada en ese caso.

## Dudas abiertas

- Ninguna. T0–T6 completadas el 2026-10-06 (fase 1 + fase 2 cerradas; ver `tasks.md`). Pendientes operativos fuera del alcance de la spec: rotación de credenciales del `.env` expuesto en el historial de git (RNF-2, decisión del usuario) y revalidación de familias ATS demovidas.
