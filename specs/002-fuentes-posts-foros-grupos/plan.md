# Plan 002 — Fuentes: posts, foros, grupos y hashtags

Referencias: `docs/constitution.md` (P3, P4, P7, P8), `spec.md`, `specs/001-.../spec.md` (los filtros se reutilizan sin cambios).

## Módulos

- `src/scrapers/registry.py`: registro único de fuentes aprobadas: nombre, tipo (`job_board` | `post` | `forum`), estado (`enabled` / `disabled` / `pending`), causa y límite de peticiones; construye la lista de scrapers solo con las habilitadas y disponibles (credenciales/dependencias presentes). Cubre RF-1, RF-5 (gate), RF-6, RF-11 (gate), RF-12, RF-13.
- `src/scrapers/hn.py`: Hacker News vía API de Algolia (tablero `tags=job` + hilos de contratación). Cubre RF-2.
- `src/scrapers/mastodon.py`: timelines públicos de hashtags por instancia. Cubre RF-4.
- `src/scrapers/reddit.py` (ampliación): más subreddits + búsquedas por flair/términos; se deshabilita con causa si faltan credenciales. Cubre RF-5.
- `src/scrapers/linkedin_posts.py`: publicaciones con hashtags vía Playwright con la sesión del usuario; se deshabilita si faltan credenciales o Playwright; se detiene ante CAPTCHA/restricción. Cubre RF-11.
- `src/scrapers/infojobs.py`, `src/scrapers/builtin.py`, `src/scrapers/web3career.py`: job boards aprobados, accesibles (verificado 200) y de HTML servido. Cubre RF-13 (ola 1).
- `src/scrapers/base.py`: presupuesto de peticiones por fuente y `normalize_url`. Cubre RF-8, RF-9.
- `src/main.py`: scrapers desde el registro, dedup en dos niveles, log por fuente con causa si falla. Cubre RF-1, RF-6, RF-8.
- `tests/fixtures/`: respuestas JSON/HTML por fuente para tests sin red (RNF-3).

> `src/scrapers/remoteok.py` se elimina (RF-12) y `remoteok` queda en `blocked_sources`.

## Modelo de datos

Entrada del registro (`src/scrapers/registry.py`, fuente de verdad de fuentes; `profile.json` conserva keywords/subreddits/hashtags):

```text
SourceSpec:
  name: str               — id estable ("hackernews", "linkedin_posts", ...)
  kind: str               — "job_board" | "post" | "forum"
  status: str             — "enabled" | "disabled" | "pending"
  reason: str             — causa cuando no está habilitada (credenciales, 403, pendiente...)
  builder: Callable       — fabrica el scraper o None si no está implementado
  max_requests: int       — presupuesto por ejecución (RF-9)
```

`JobPost` para fuentes de tipo `post`:

```text
title, company (nunca inventada; "" si no se detecta), description, url,
source, posted_date, is_remote
```

## Algoritmo / flujo principal

1. `get_scrapers()` consulta el registro → construye solo `status=enabled` con credenciales/dependencias presentes; loguea el resto con causa (RF-6, RF-13).
2. Cada scraper normaliza a `JobPost` con su parser (probado con fixture) y respeta su presupuesto de peticiones (RF-9).
3. `scrape_all` continúa ante errores por fuente y registra el motivo (RF-6).
4. Dedup: URL canónica → título+empresa normalizados (RF-8).
5. Filtros spec 001 → scoring → reporte (flujo intacto).

## Decisiones justificadas

### Decisión 1: registro de fuentes en código (estructura) con estado y causa
- **Elegido:** `SourceSpec` dataclass-list en `registry.py`.
- **Alternativa descartada:** JSON de configuración de fuentes.
- **Motivo:** RF-12/RF-13 necesitan garantizar que una fuente bloqueada **nunca** se construya; eso es más seguro como código revisable que como dato editable; el `reason` visible mantiene la trazabilidad pedida.

### Decisión 2: APIs públicas antes que scraping HTML
- **Elegido:** Algolia (HN) y Mastodon API primero; boards con HTML servido después.
- **Alternativa descartada:** parsear SPAs/páginas con reto anti-bot.
- **Motivo:** P3, RNF-3; evidencia: Indeed/Tecnoempleo/Dice/FlexJobs/Fiverr responden 403 y Welcome to the Jungle devuelve 202 (reto) → `pending`, sin eludir controles (RF-10).

### Decisión 3: gate de credenciales por fuente
- **Elegido:** Reddit/LinkedIn posts se construyen solo si sus credenciales y dependencias existen; si no, `disabled` con causa.
- **Alternativa descartada:** lanzar y fallar en runtime, o ejecutar vacío silenciosamente (comportamiento actual de Reddit: 0 ofertas sin aviso).
- **Motivo:** RF-5/RF-11, RF-6; hoy el `.env` no tiene credenciales de Reddit/LinkedIn.

### Decisión 4: no se crea una super-clase de "scraper de posts"
- **Elegido:** cada fuente implementa `BaseScraper` y normaliza a `JobPost`.
- **Alternativa descartada:** jerarquía `PostScraper` con lógica compartida.
- **Motivo:** P8; la normalización compartida ya existe (`filter_keyword_jobs`/`matches_keywords`).

### Decisión 5: dedup en dos niveles
- **Elegido:** URL canónica primero, título+empresa como respaldo.
- **Alternativa descartada:** solo título+empresa (actual).
- **Motivo:** RF-8: el mismo anuncio llega por varias fuentes con URL distinta.

### Decisión 6: los posts no se prefiltran por keywords en el scraper (2026-10-06, aprobada por el usuario)
- **Elegido:** `filter_keyword_jobs` deja pasar todo job con `post_source=True`; el gate de relevancia del matcher (RF-13, spec 001) decide y registra la causa.
- **Alternativas descartadas:** ampliar `search_keywords` con "QA"/términos españoles (cambia el scope de búsqueda aprobado) o dejar HN/InfoJobs en 0 (inutiliza RF-2).
- **Motivo:** evidencia viva: HN 18 en bruto → 0 con el gate (`Company Is Hiring` no contiene roles); InfoJobs y títulos en español tampoco pasan keywords inglesas. El pre-gate duplicaba la puerta de relevancia ya aprobada en RF-13.

## Contrato público (API / CLI / interfaz)

- `get_scrapers() -> List[BaseScraper]` — ahora derivado del registro (misma firma).
- `list_sources() -> List[SourceSpec]` — inventario con estados/causas (nuevo, RF-13).
- `normalize_url(url) -> str` — utilidad de dedup (nueva).
- Log: por fuente: `ok/cantidad` o `DISABLED (causa)` / `ERROR (causa)`.

## Estrategia de tests

- **Unitarios (fixtures, sin red):** parsers de HN, Mastodon, Reddit, InfoJobs, Built In, web3.career; `normalize_url`; presupuesto por fuente; gates de credenciales.
- **Integración:** registro → scrapers habilitados esperados → run simulado → dedup → filtros spec 001.
- **Resiliencia:** fuente que lanza excepción → las demás siguen y el resumen lo reporta (RF-6).
- **Bloqueo:** `remoteok` no aparece en `get_scrapers()` aunque se pida (RF-12).

## Mapeo RF → módulo → test

| RF | Módulo | Test |
|----|--------|------|
| RF-1 | `scrapers/registry.py` | `tests/test_registry.py::test_only_enabled_sources` |
| RF-2 | `scrapers/hn.py` | `tests/test_hn.py::test_parse_hiring_thread` |
| RF-3 | registro (`bluesky` pending) | `tests/test_registry.py::test_bluesky_disabled_with_reason` |
| RF-4 | `scrapers/mastodon.py` | `tests/test_mastodon.py::test_parse_tag_timeline` |
| RF-5 | `scrapers/reddit.py` + registry | `tests/test_reddit.py::test_disabled_without_credentials` / `::test_search_hiring_posts` |
| RF-6 | `main.scrape_all` | `tests/test_scrape_all.py::test_failing_source_does_not_abort` |
| RF-7 | `scrapers/base.py` | `tests/test_matcher.py::test_post_jobs_pass_same_filters` |
| RF-8 | `main.dedup_jobs` | `tests/test_dedup.py::test_canonical_url_dedup` |
| RF-9 | `scrapers/base.py` | `tests/test_base.py::test_request_budget_per_source` |
| RF-10 | revisión + registro | validación: fuentes 403 quedan `pending` con causa |
| RF-11 | `scrapers/linkedin_posts.py` + registry | `tests/test_registry.py::test_linkedin_posts_gated` |
| RF-12 | `scrapers/registry.py` | `tests/test_registry.py::test_remoteok_blocked` |
| RF-13 | `scrapers/registry.py` + parsers | `tests/test_registry.py::test_approved_sources_have_status` |
