# Spec 002 — Fuentes: posts, foros, grupos y hashtags

## Contexto y objetivo

Hoy el bot cubre job boards (RemoteOK, Remotive, We Work Remotely, Arbeitnow, Himalayas, Indeed, GetOnBoard), Reddit (solo `new.json` de 5 subs) y LinkedIn **Jobs** (guest API). El usuario necesita cobertura de "todo internet": publicaciones con hashtags de contratación (`#hiring`, "estamos buscando", "we're hiring"), foros, grupos y comunidades — no solo listados formales, porque en los boards de LinkedIn con postulación rápida casi nunca se consigue trabajo.

Esta spec amplía las fuentes de forma **ética, legal y sin bloqueos**: APIs públicas y endpoints abiertos, con rate limiting e identificación. Cada fuente nueva se declara en configuración y pasa por los mismos filtros de la spec 001.

## Usuarios / actores

- **José**: necesita ver ofertas publicadas en posts/foros/grupos, no solo en job boards.
- **Mantenimiento**: necesita añadir/quitar fuentes sin tocar la lógica central y sin romper la ejecución si una fuente falla.

## Historias de usuario

- H1: Como José quiero que el bot busque publicaciones con hashtags de contratación para encontrar oportunidades que nunca llegan a los job boards.
- H2: Como José quiero que se incluyan foros y comunidades (HN, Reddit ampliado) para cubrir contratación informal y de startups.
- H3: Como mantenedor quiero que una fuente caída no aborte el run para seguir recibiendo el reporte parcial.
- H4: Como mantenedor quiero una lista de fuentes aprobadas para que nadie añada scrapers sin decisión.

## Requisitos funcionales (criterios de aceptación en EARS)

- RF-1: EL SISTEMA mantiene una lista de fuentes aprobadas en configuración (`profile.json → platforms.sources` o `config.py`), cada una con tipo (`job_board` | `post` | `forum`) y estado habilitado/deshabilitado; añadir o quitar una fuente es un cambio de configuración o de una tarea con RF.
- RF-2: CUANDO Hacker News está habilitado, EL SISTEMA consulta la API pública de Algolia (`hn.algolia.com`): (a) el tablero de empleos (`tags=job`) y (b) publicaciones/hilos de contratación ("hiring", "who is hiring") recientes según `MAX_DAYS_OLD`, extrayendo los puestos candidatos.
- RF-3: CUANDO Bluesky está habilitado **y su API responde desde el entorno de ejecución**, EL SISTEMA busca posts públicos por hashtags/términos de contratación (`#hiring`, `#vacante`, `estamos buscando`, `we're hiring`) y extrae los puestos candidatos. **Evidencia (2026-10-06):** `public.api.bsky.app` devuelve **403** desde este entorno; hasta confirmar disponibilidad la fuente queda `enabled: false`.
- RF-4: CUANDO Mastodon está habilitado, EL SISTEMA consulta timelines públicos de hashtags de contratación en instancias configuradas vía su API pública (verificado: responde 200 sin credenciales).
- RF-5: CUANDO Reddit está habilitado **y hay credenciales de API configuradas**, EL SISTEMA amplía la búsqueda más allá de `new.json`: consulta subreddits adicionales y búsquedas por flair/términos de contratación (`[Hiring]`, `flair:hiring`), manteniendo el soporte autenticado con `praw`. **Evidencia (2026-10-06):** el endpoint JSON sin autenticación responde **403**; sin credenciales la fuente se deshabilita en lugar de fallar en silencio (hoy `RedditScraper` devuelve 0 ofertas sin avisar).
- RF-6: CUANDO una fuente está deshabilitada o falla, EL SISTEMA registra el motivo, continúa con el resto de fuentes y el reporte se genera con lo obtenido (una fuente caída no aborta la ejecución).
- RF-7: CUANDO una oferta proviene de una fuente de tipo `post`, EL SISTEMA la normaliza al mismo modelo `JobPost` y aplica los mismos filtros (spec 001) que a una de job board.
- RF-8: EL SISTEMA deduplica el resultado final por URL canónica (sin fragmentos/parámetros de tracking) y, como segundo nivel, por título+empresa normalizados.
- RF-9: EL SISTEMA identifica sus peticiones (User-Agent reconocible con contacto) y aplica un límite de peticiones por fuente y por ejecución (`max_requests_per_source`, objetivo ≤ 30), sin eludir CAPTCHAs, bloqueos ni controles anti-bot.
- RF-10: EL SISTEMA solo usa fuentes públicas, APIs permitidas o credenciales propias del usuario; cualquier fuente que requiera eludir controles queda fuera de alcance hasta nueva decisión.
- RF-11: CUANDO LinkedIn está habilitado con credenciales del usuario (`LINKEDIN_EMAIL`/`LINKEDIN_PASSWORD`) y Playwright disponible, EL SISTEMA busca publicaciones (feed y búsquedas) con hashtags/términos de contratación (`#hiring`, `#remoto`, `estamos buscando`, `we're hiring`) y normaliza como `JobPost` solo las publicaciones que contengan una oferta; si LinkedIn muestra CAPTCHA, verificación o señal de restricción de la cuenta, EL SISTEMA detiene la fuente en esa ejecución, lo registra y no reintenta (no elude el control). Sin credenciales o sin Playwright, la fuente queda `disabled` con causa.
- RF-12: SI una fuente figura como no confiable en la configuración (lista `blocked_sources`), ENTONCES EL SISTEMA no la consulta bajo ninguna circunstancia; `RemoteOK` queda bloqueada por decisión del usuario (reporte de prácticas de estafa: redirección de ofertas, cancelación de suscripción impedida, contacto inexistente).
- RF-13: CUANDO un job board aprobado y accesible está habilitado en la configuración (InfoJobs, Built In, levels.fyi, arc.dev, web3.career, Lemon.io, Welcome to the Jungle, Toptal, FlexJobs, Glassdoor, Dice, Tecnoempleo, RemotoList, Talently, Google for Jobs, Fiverr, Wellfound, Remotive, We Work Remotely, Himalayas), EL SISTEMA mantiene para él: estado con causa (`enabled` / `disabled` con `reason`), su parser propio si está implementado y su test con fixture; una fuente `pending` se saltea sin romper el run.
- RF-14: CUANDO LinkedIn entrega ofertas con URL slug o `urn:li:jobPosting:{id}`, EL SISTEMA extrae el identificador correcto (con id `urn:li:jobPosting` o el id final de la URL). **Causa raíz verificada (2026-10-06):** el patrón actual `/jobs/view/{número}` no coincide con las URLs actuales y la fuente devuelve **0 ofertas**.
- RF-15: EL SISTEMA confía en la vigencia de las fuentes con feed/API oficial (RSS o JSON publicado por la propia plataforma) y omite la verificación por oferta; la verificación de actividad queda para el HTML scraping. **Causa raíz verificada (2026-10-06):** We Work Remotely entrega 67 ofertas por RSS y 0 activas tras `verify_job_active` (comprobaciones por subcadena frágiles), e Himalayas 11 → 0 por URLs externas; la verificación por oferta además añade una petición HTTP por oferta.

## Requisitos no funcionales

- RNF-1: El tiempo total de scraping por ejecución no supera 10 minutos en local (objetivo, medible con log por fuente).
- RNF-2: Ninguna fuente comparte estado mutable con otra salvo la sesión de deduplicación; añadir una fuente no modifica el matcher.
- RNF-3: Los tests de las fuentes corren sin red (parsers probados con fixtures HTML/JSON).
- RNF-4: La configuración de fuentes es legible por una persona y no duplica keywords maestras (se reutilizan `search_keywords`).

## Casos límite

- API externa caída o con rate limit → se registra y se continúa (RF-6).
- Post de contratación sin empresa identificable → se conserva con empresa `""` o el dominio detectable; no se inventa.
- Hashtag ambiguo (`#hiring` con contenido no laboral) → lo filtra la spec 001 (score mínimo), no se fuerza.
- Fuente que devuelve duplicados internos → dedup por URL canónica (RF-8).
- Ejecución en GitHub Actions (sin credenciales) → las fuentes con credenciales se deshabilitan solas.

## Fuera de alcance

- Discord (requiere token de bot), X/Twitter (API de pago).
- Fuentes con bloqueo anti-bot o paywall desde este entorno (verificadas con 403/reto: Indeed, Tecnoempleo, Dice, FlexJobs, Fiverr; retador: Welcome to the Jungle) → quedan `pending` hasta decisión nueva; no se eluden controles (RF-10).
- Fuentes con dominio no identificado en la solicitud del usuario (`talently`, `remotelist`) → `pending` hasta confirmar URL.
- Postulación automática (spec 003).

## Criterios de finalización

- [ ] Todos los RF tienen al menos un test que los cubre.
- [ ] Todos los RNF verificables están medidos o evidenciados.
- [ ] Los casos límite están cubiertos.
- [ ] La suite de tests pasa en verde.
- [ ] No hay código sin RF que lo justifique.

## Decisiones tomadas (2026-10-06, aprobadas por el usuario)

- **Fuentes inmediatas verificadas:** Hacker News (Algolia) y Mastodon (200 sin credenciales) se implementan ahora; Reddit ampliado y Telegram se implementan con detección de credenciales (hoy vacías → `disabled` con causa); LinkedIn posts con hashtags aprobado por el usuario a sabiendas del riesgo de restricción → requiere credenciales + Playwright, con parada ante CAPTCHA/restricción (RF-11).
- **RemoteOK:** eliminada y bloqueada (reporte del usuario de prácticas de estafa). Ver RF-12.
- **Job boards aprobados:** la lista completa del usuario queda registrada en la configuración con estado y causa (RF-13); se implementan primero los verificables y accesibles.
- **Bluesky:** queda `disabled` mientras su API devuelva 403 desde el entorno.
- **Gate de keywords para posts (2026-10-06, aprobada opción A):** las fuentes de tipo post/comentario (`post_source=True`: HackerNews tablero+hilo, Mastodon, LinkedIn posts) **no** se prefiltran por `search_keywords`; quien decide la relevancia es el gate del matcher (RF-13 de spec 001, `role_relevance`/`job_titles_fit`, score ≥ 20), con su causa visible en el log de descartes. Motivo: los títulos de posts (`Company Is Hiring`, ofertas en español, `Company | Role | Location`) no alcanzan las keywords inglesas y la fuente quedaba en 0 de forma silenciosa. Las fuentes de feed de empleos sí conservan el pre-gate de keywords.
