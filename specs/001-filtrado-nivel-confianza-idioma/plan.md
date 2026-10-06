# Plan 001 — Filtrado por nivel, confianza e idioma

Referencias: `docs/constitution.md` (P1, P2, P4, P7), `spec.md`.

## Módulos

- `src/analyzer/filters.py`: filtros puros y configurables. `LevelFilter` (RF-1, RF-2, RF-3), `TrustFilter` (RF-4, RF-5), `LanguageFilter` (RF-6, RF-7). Cada filtro devuelve `None` (pasa) o un código de motivo.
- `src/analyzer/matcher.py`: orquestación. `_is_excluded` pasa a devolver el motivo en vez de `bool`; `filter_jobs` separa elegibles/descartados, aplica el bono de RF-7 y expone `last_excluded`. Cubre RF-9.
- `src/scrapers/base.py`: `JobPost.excluded_reason: Optional[str]` para trazabilidad (RF-9).
- `src/scrapers/linkedin.py`: ventana coherente con `MAX_DAYS_OLD` y parseo de `<time datetime>` de las tarjetas (RF-8). **Nota:** `f_E` no se envía porque se verificó que el guest API lo ignora (evidencia en spec).
- `src/main.py`: resumen de descartes por motivo en el log (RF-9, RNF-4).
- `cvs/profile.json`: nuevos bloques `level_filter`, `trust_filter`, `language_filter`; `QA Lead` movido de `job_titles_fit` a `exclude_titles` (sujeto a decisión).
- `tests/`: unitarios de cada filtro, integración con `JobMatcher`, sin red.

## Modelo de datos

`cvs/profile.json` (nuevos bloques):

```json
"level_filter": {
  "excluded_title_markers": ["senior", "sr.", "sénior", "lead", "staff", "principal", "head of", "director", "chief", "manager", "architect"],
  "excluded_title_patterns": ["\\b(ii|iii|iv)\\b"],
  "min_years_excluded": 5,
  "years_patterns": ["(\\d+)\\s*\\+?\\s*(years|años)"],
  "allowed_title_markers": ["junior", "jr", "entry", "intern", "trainee", "mid", "beca", "grad", "practicant"]
},
"trust_filter": {
  "blocked_companies": ["BairesDev", "..."],
  "scam_signals": ["pago para aplicar", "fee to apply", "investment required", "..."]
},
"language_filter": {
  "rejected_english_levels": ["c1", "c2", "native", "fluent", "proficient", "bilingual"],
  "spanish_bonus": 5,
  "spanish_markers": ["español", "latam", "venezuela", "..."]
}
```

`JobPost.excluded_reason: Optional[str]` — uno de `nivel_senior`, `experiencia_excesiva`, `empresa_bloqueada`, `senal_scam`, `idioma_no_alcanzado`, `titulo_no_apto`, `ubicacion_no_apta`, `no_remoto`, `idioma_no_latino`.

## Algoritmo / flujo principal

1. `JobMatcher.filter_jobs` recorre cada oferta y, en orden, aplica: confianza → idioma → nivel → experiencia → remote/geografía (orden conservado del `_is_excluded` actual, con confianza primero).
2. Cada filtro es una clase sin estado que solo lee `profile.json`; devuelve código de motivo o `None`.
3. Oferta elegible → scoring actual (sin cambios) + bono de español (RF-7), tope 100.
4. Oferta descartada → se guarda `(fuente, título, motivo)` en `matcher.last_excluded` y el log imprime el resumen por motivo.

## Decisiones justificadas

### Decisión 1: filtros como módulos puros aparte del scoring
- **Elegido:** clases `LevelFilter`/`TrustFilter`/`LanguageFilter` en `src/analyzer/filters.py`.
- **Alternativa descartada:** seguir agregando `if` en `matcher._is_excluded`.
- **Motivo:** RNF-2 (reglas configurables) + testeo aislado por RF; el matcher ya tiene 6 responsabilidades.

### Decisión 2: prioridad de motivos de descarte
- **Elegido:** confianza > idioma > nivel > experiencia > remote/geografía.
- **Alternativa descartada:** primer filtro que coincida en orden arbitrario.
- **Motivo:** un motivo estable facilita el diagnóstico (RF-9) y evita ruido: una estafa con título senior se reporta como `empresa_bloqueada`/`senal_scam`, que es lo accionable.

### Decisión 3: reglas en `profile.json`, no en `config.py`
- **Elegido:** niveles, años, blocklist, señales y bono viven en `cvs/profile.json` (ya es la fuente del perfil).
- **Alternativa descartada:** variables de entorno nuevas en `.env`.
- **Motivo:** RNF-2 y consistencia con el matcher actual; `.env` queda para secretos/credenciales (P4).

### Decisión 4: años mínimo ≥ 5 excluye, rangos con mínimo < 5 no
- **Elegido:** leer el mínimo del rango declarado.
- **Alternativa descartada:** excluir si el máximo del rango llega a 5 (mataría "3-5 años", apto para mid).
- **Motivo:** RF-2; sensibilidad hacia el usuario junior/mid sin perder ofertas "3-4 años".

## Contrato público (API / CLI / interfaz)

- `JobMatcher.filter_jobs(jobs) -> List[JobPost]` (misma firma; solo se añaden elegibles tras nuevos filtros).
- `JobMatcher.last_excluded -> List[Tuple[str, str, str]]` → `(source, title, reason)` (nuevo, RF-9).
- `LevelFilter.check(job, cfg) -> Optional[str]`; igual para `TrustFilter` y `LanguageFilter`.
- Log: línea `Filtered: nivel_senior=N empresa_bloqueada=M ...` al terminar el scraping (nuevo).

## Estrategia de tests

- **Unitarios:** cada filtro con fixtures de ofertas (título senior, "5+ years", "3-5 years", sin nivel, C1, "Sénior", blocklist, scam signal, español/LATAM).
- **Integración:** `JobMatcher` completo con un `profile.json` de prueba: una oferta senior no llega al reporte, una junior sí, el bono no supera 100.
- **Regresión:** ofertas remote/geografía/sin latinos siguen comportándose igual (tests de los filtros preexistentes).
- **Sin red:** la suite no hace peticiones.

## Mapeo RF → módulo → test

| RF | Módulo | Test |
|----|--------|------|
| RF-1 | `filters.LevelFilter` | `tests/test_filters.py::test_senior_titles_excluded` |
| RF-2 | `filters.LevelFilter` | `tests/test_filters.py::test_five_years_excluded` / `::test_range_3_5_allowed` |
| RF-3 | `filters.LevelFilter` | `tests/test_filters.py::test_unspecified_level_allowed` |
| RF-4 | `filters.TrustFilter` | `tests/test_filters.py::test_blocked_company` |
| RF-5 | `filters.TrustFilter` | `tests/test_filters.py::test_scam_signals` |
| RF-6 | `filters.LanguageFilter` | `tests/test_filters.py::test_english_c1_rejected` / `::test_b2_allowed` |
| RF-7 | `matcher` | `tests/test_matcher.py::test_spanish_bonus_caps_at_100` |
| RF-8 | `scrapers.linkedin` | `tests/test_linkedin_params.py::test_window_and_posted_date` |
| RF-9 | `matcher` + `main` | `tests/test_matcher.py::test_excluded_reasons_recorded` |
| RF-10 | `tests/test_filters.py::test_no_dead_filter_lists` | inspecciona `Config`/`profile.json` y exige consumo |
