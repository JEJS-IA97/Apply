# Spec 001 — Filtrado por nivel, confianza e idioma

## Contexto y objetivo

El bot hoy reporta casi solo ofertas **senior**, pese a que el usuario es junior/mid. Causa raíz detectada (revisión de código, sin cambios todavía):

1. `src/config.py:64` define `exclude_terms` ("hybrid", "on-site", "senior staff", "principal") pero **nadie lo consume** (grep: solo la definición).
2. `src/analyzer/matcher.py` no tiene ninguna regla de nivel: no excluye "senior", "lead", "staff", "principal", "director" ni años de experiencia exigidos.
3. El scoring favorece ofertas senior: al listar más skills, sube `_score_skill_match` (ratio de `core_skills` cubiertos) y el título "Senior QA Automation Engineer" contiene `job_titles_fit` → 40 pts.
4. `src/scrapers/linkedin.py` no parsea la fecha de publicación de las tarjetas ni usa términos junior de `profile.json`; la ventana es de 24 h (`f_TPR=r86400`), lo que reduce el pool y hace que predomine lo que haya fresco.
5. No hay filtro de confianza (empresas bloqueadas / señales de scam) ni de nivel de inglés exigido.

Este ajuste garantiza que el reporte diario contenga solo ofertas que José pueda ejercer: nivel junior/mid o sin nivel, remoto, idioma español o inglés hasta B2, geografía permitida y sin estafas.

## Usuarios / actores

- **José**: recibe el reporte diario; necesita que todo lo que llegue sea aplicable y legítimo.
- **Mantenimiento (agente/usuario)**: necesita auditar por qué una oferta fue descartada.

## Historias de usuario

- H1: Como José quiero que el bot descarte ofertas senior/staff/director para no recibir puestos que no puedo ejercer.
- H2: Como José quiero que se descarten empresas bloqueadas y señales de scam para no exponerme a fraudes.
- H3: Como José quiero que se descarten las que exigen inglés C1+ y se prioricen las en español para poder postular.
- H4: Como mantenedor quiero ver el motivo de cada descarte para auditar los filtros.

## Requisitos funcionales (criterios de aceptación en EARS)

- RF-1: CUANDO el título de la oferta contiene un marcador de nivel senior o por encima (senior, sr., sénior, lead, staff, principal, head of, director, chief, "nivel gerencial", II/III/IV como sufijo de puesto), EL SISTEMA excluye la oferta del reporte con motivo `nivel_senior`.
- RF-2: CUANDO la descripción exige 5 o más años de experiencia (mínimo declarado ≥ 5) y el título no indica nivel junior/entry/mid, EL SISTEMA excluye la oferta con motivo `experiencia_excesiva`. Los rangos cuyo mínimo sea menor a 5 (ej. "3-5 años") no excluyen.
- RF-3: CUANDO la oferta no especifica nivel ni años mínimos exigidos, ENTONCES EL SISTEMA la conserva como elegible (nivel no especificado).
- RF-4: CUANDO la empresa/marca figura en la lista de bloqueadas del perfil, ENTONCES EL SISTEMA excluye la oferta con motivo `empresa_bloqueada`.
- RF-5: CUANDO la oferta contiene al menos una señal de scam configurable (pago o cargo por postular, pago inicial/inversión, promesa de ingresos fijos semanales, "trabaja desde casa ganando X", contratación solo vía WhatsApp/mensaje personal, marca que ofrece "conseguirte empleo con IA"), ENTONCES EL SISTEMA excluye la oferta con motivo `senal_scam`.
- RF-6: CUANDO la oferta exige inglés C1, C2, native, proficient, fluent o bilingual, ENTONCES EL SISTEMA la excluye con motivo `idioma_no_alcanzado`; si no exige nivel o exige hasta B1/B2/intermediate, la conserva.
- RF-7: CUANDO la oferta está en español o su mercado es LATAM/España, ENTONCES EL SISTEMA suma un bono configurable al score (sin superar 100) para priorizarla en el reporte.
- RF-8: CUANDO se consulta LinkedIn, EL SISTEMA usa una ventana de búsqueda coherente con `MAX_DAYS_OLD` y parsea la fecha de publicación de cada tarjeta (`<time datetime>`), de modo que no se recojan ofertas fuera de ventana. **Evidencia (2026-10-06, medición directa):** el parámetro de experiencia `f_E` es ignorado por el guest API (resultados idénticos con y sin él), por lo que el control de nivel en el origen no es posible y recae en RF-1/RF-2 (matcher) y en los términos de búsqueda.
- RF-9: EL SISTEMA registra para cada oferta descartada su fuente, título y motivo de descarte, sin incluirla en el correo.
- RF-10: EL SISTEMA no mantiene listas de filtrado declaradas y sin uso: todo campo de `config.py` o `cvs/profile.json` que represente una regla de filtrado debe estar conectado al `JobMatcher` o eliminarse (verificable por test).
- RF-11: EL SISTEMA solo menciona en la carta de presentación habilidades presentes en `cvs/profile.json` (fuente aprobada del CV); nunca usa listas alternativas que incluyan habilidades declaradas fuera del CV (hoy `src/profile.py` incluye Selenium, Pytest, Cucumber, TailwindCSS, Vite y Azure, que `profile.json` marca como "not on CV").
- RF-12: CUANDO una oferta llega sin descripción y la fuente permite obtenerla con la misma petición de verificación de vigencia (LinkedIn), EL SISTEMA adjunta la descripción antes de puntuar, de modo que los filtros de años/idioma y el scoring operen sobre datos reales.
- RF-13: EL SISTEMA exige relevancia mínima de rol para aprobar una oferta: el título debe coincidir con un `job_titles_fit` o con las familias del perfil (QA/calidad/automatización/testing, frontend/React, DevOps); puestos sin relación (data, compliance, marketing, ventas...) no superan el umbral aunque compartan skills genéricas. **Evidencia (2026-10-06):** hoy pasan "Data Engineer, Data Quality" (34%) o "Compliance Automation Analyst" (42%) con el umbral 20.
- RF-14: CUANDO `GEMINI_API_KEY` está configurada, EL SISTEMA genera la carta de presentación con un modelo Gemini de Google (API REST de `generativelanguage.googleapis.com`); CUANDO la clave no está configurada o la llamada falla (red, error del modelo, respuesta vacía), EL SISTEMA usa la plantilla actual sin interrumpir el reporte. El proveedor OpenAI se elimina: código, dependencia `openai` y secreto `OPENAI_API_KEY`. La clave se toma solo de `.env` o de los secretos de Actions; nunca se escribe en el repositorio.

## Requisitos no funcionales

- RNF-1: El filtrado es local (sin llamadas de red) y añade overhead despreciable por oferta (objeto: < 5 ms/oferta en CPU local).
- RNF-2: Todas las reglas (niveles, años, empresas bloqueadas, señales de scam, umbral de inglés, bono por español) son configurables desde `cvs/profile.json` sin tocar código.
- RNF-3: La suite de tests corre sin conexión.
- RNF-4: Los motivos de descarte son legibles en el log de ejecución (resumen por motivo).

## Casos límite

- Títulos en español ("Sénior", "Líder", "Gerente") y abreviaturas ("Sr.", "Sr").
- "Mid-Senior level" → excluido por RF-1 (decisión registrada en dudas abiertas).
- Rango "3-5 años" → no excluye; "5-7 años" o "5+ años" → excluye (RF-2).
- Empresa desconocida sin señales de scam → se conserva (no se bloquea por desconocida).
- Oferta ya excluida por múltiples reglas → se registra el primer motivo en orden: confianza > idioma > nivel > experiencia > remote/geografía (consistente con el orden actual de `_is_excluded`).
- El filtro existente de scripts no latinos y de remote se conserva sin cambios.

## Fuera de alcance

- Postulación automática (`specs/003-postulacion-automatica`).
- Nuevas fuentes de ofertas (`specs/002-fuentes-posts-foros-grupos`).
- Detección de scams por IA o modelos externos.

## Criterios de finalización

- [ ] Todos los RF tienen al menos un test que los cubre.
- [ ] Todos los RNF verificables están medidos o evidenciados.
- [ ] Los casos límite están cubiertos.
- [ ] La suite de tests pasa en verde.
- [ ] No hay código sin RF que lo justifique.

## Decisiones tomadas (2026-10-06, aprobadas por el usuario)

- **Nivel objetivo:** junior/mid + ofertas sin nivel especificado. Se excluyen senior, sr., lead, staff, principal, director, manager, jefaturas y sufijos II/III/IV, además de ofertas que exigen 5+ años de experiencia. `QA Lead` sale de `job_titles_fit` y pasa a `exclude_titles`.
- **Umbral de años:** mínimo declarado ≥ 5 años excluye; rangos con mínimo < 5 (ej. "3-5 años") no excluyen.
- **Alcance de confianza:** blocklist con BairesDev y marcas de "empleo con IA" (dejada editable en `profile.json`), más señales genéricas de scam (pago por postular, pago inicial, ingresos garantizados, contratación solo por WhatsApp).
- **Proveedor de cartas IA (RF-14, 2026-10-06, aprobada por el usuario):** Gemini (`GEMINI_API_KEY`) **reemplaza** a OpenAI — el usuario no tiene clave OpenAI y aportó la de Gemini "para reemplazar OpenAI". Se elimina `openai==0.28.1` y el secreto `OPENAI_API_KEY` (borrado de GitHub el 2026-10-06); fallback a plantilla ante cualquier fallo, igual que antes.
