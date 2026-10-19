# Spec 004 — Reporte útil, nuevas fuentes y front en GitHub Pages

## Contexto y objetivo

José reporta (2026-10-19) que el correo diario solo trae ofertas "senior" o con match ≤ 50 %, mientras que una búsqueda manual el mismo día encontró varias ofertas junior/mid con buen encaje. Revisión del correo del 2026-10-16 (7 ofertas, 25–48 %) y del código:

1. **Escala de puntaje rota.** `_score_skill_match` divide entre las ~40 skills del CV, así que una oferta muy afín suma 4–8 de 40 puntos. El título genérico "Software Engineer" recibe los mismos 40 puntos que "QA Automation Engineer". Resultado: casi todo cae entre 25 y 50 %, y el porcentaje no distingue una oferta buena de una mala.
2. **Puntaje en 0 por una sola mención** de una skill de `skills_not_on_cv` (Selenium, Docker, BDD…), con coincidencia por subcadena ("tdd" dentro de otras palabras). Así se descartaban ofertas de QA perfectamente aplicables.
3. **Sin filtro de elegibilidad geográfica.** Solo se excluye Asia, así que llegan ofertas solo para EE. UU., España o Berlín.
4. **Sin filtro de idioma de la publicación.** Llegan avisos en alemán o portugués.
5. **Umbral mínimo de 20.** Casi cualquier oferta con un título parecido pasa.
6. **LinkedIn sin pausas.** 24 consultas seguidas más el detalle de cada oferta: LinkedIn bloquea, no llegan ofertas de LinkedIn y casi ninguna tiene descripción (los filtros de años no pueden actuar).
7. **Fuentes con mejores ofertas para Venezuela fuera del bot.** Torre (bolsa "trabajo-remoto-venezuela") y Get on Board tienen API pública; el scraper de Get on Board usa una ruta HTML que ya no existe.
8. **Variables de entorno.** `.env` usa `SMTP_HOST/SMTP_USER/SMTP_PASS/REPORT_TO/DATABASE_URL`; el código solo lee `SMTP_SERVER/EMAIL_FROM/EMAIL_PASSWORD/EMAIL_TO/MONGO_URI`. En local no se envía el correo.
9. **Nuevas familias de empleo** pedidas por José: diseño UI/UX y gráfico, y administrativo/asistente/data entry. Hoy el perfil las excluye explícitamente.

## Requisitos funcionales (EARS)

- RF-1: EL SISTEMA calcula el puntaje (0–100) como: familia del título (QA 45, frontend 35, diseño 30, administrativo 25, desarrollo genérico 15) + skills del CV encontradas (hasta 35, saturando en 6 skills distintas) + bono hispano/LATAM (hasta 10) + bono de nivel junior/mid/sin experiencia (5) + afinidad de empresa (hasta 5) − penalización por skills fuera del CV (4 por skill, hasta 16).
- RF-2: CUANDO la descripción menciona una skill de `skills_not_on_cv`, EL SISTEMA resta puntos (RF-1) en lugar de anular el puntaje, y la coincidencia es por palabra completa.
- RF-3: CUANDO la ubicación de la oferta nombra países o ciudades y ninguno pertenece a la lista permitida (Venezuela, países de LATAM, "Latin America", "LATAM", "Americas", "Worldwide", "Anywhere", "Global"), EL SISTEMA la excluye con motivo `ubicacion_no_elegible`. CUANDO la descripción exige residir en un país no permitido ("must reside in the US", "based in Spain"), también la excluye con ese motivo.
- RF-4: CUANDO el texto de la oferta está mayoritariamente en alemán, portugués o francés, EL SISTEMA la excluye con motivo `idioma_publicacion`.
- RF-5: EL SISTEMA solo incluye en el correo las ofertas con puntaje ≥ `relevance_filter.min_score` (por defecto 55), ordenadas de mayor a menor y con un máximo de `report_limit` (por defecto 20).
- RF-6: EL SISTEMA espera `request_delay` segundos (por defecto 2) entre peticiones a LinkedIn.
- RF-7: EL SISTEMA consulta Torre (bolsa `trabajo-remoto-venezuela`, páginas HTML + API `api/suite/opportunities/<id>`) y Get on Board (API `api/v0/search/jobs`), con presupuesto de peticiones. De Get on Board solo conserva ofertas `fully_remote`.
- RF-8: EL SISTEMA acepta como alias `SMTP_USER`→`EMAIL_FROM`, `SMTP_PASS`→`EMAIL_PASSWORD`, `REPORT_TO`→`EMAIL_TO`, `SMTP_HOST`→`SMTP_SERVER`, `DATABASE_URL`→`MONGO_URI`.
- RF-9: EL SISTEMA reconoce las familias diseño y administrativo (títulos y patrones en `profile.json`) y deja de excluir esos títulos.
- RF-10: EL SISTEMA exporta las ofertas filtradas a `docs/data/jobs.json` (fuente, familia, puntaje, motivos, enlace, correo de postulación si la descripción indica postular por email). El archivo conserva las ofertas de los últimos 30 días y las marcadas como `curated`.
- RF-11: EL SISTEMA publica en `docs/` (GitHub Pages) una página estática que lee `docs/data/jobs.json`, permite filtrar por familia y fuente, marcar postulaciones (almacenamiento local del navegador) y, para las ofertas que se postulan por correo, abre un borrador de Gmail desde `jose.e.jimenez.1411@gmail.com` con asunto y cuerpo prellenados. El envío lo hace siempre José; la página no envía nada por sí sola.

## Requisitos no funcionales

- RNF-1: Sin dependencias nuevas en Python; el front es HTML/CSS/JS sin build.
- RNF-2: Ningún secreto en `docs/`. El JSON publicado no incluye datos que no estén ya en la oferta pública.
- RNF-3: Los tests existentes siguen pasando; cada RF nuevo tiene al menos un test.

## Fuera de alcance

- Envío automático de correos de postulación.
- Scraping de sitios que requieren login o tienen anti-bot (Indeed, Glassdoor…).
