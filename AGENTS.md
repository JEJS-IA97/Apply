# AGENTS.md — Apply

Este archivo es el contrato operativo del agente. Las reglas del proyecto no deben interpretarse por fragmentos aislados: la jerarquía siguiente determina qué documento manda.

## Jerarquía de autoridad

1. **Solicitud del usuario.** Puede cambiar el alcance, pero todo cambio de comportamiento debe quedar reflejado en la spec antes de implementarse.
2. **Constitución aprobada** en `docs/constitution.md`.
3. **Spec y plan aprobados** de la feature activa.
4. **Este AGENTS.md**: reglas operativas generales.
5. **ANTI_VIBECODE_GUIDE.md** y `ANTI_VIBECODE_STANDARD.json`: estándares de calidad y guardrails.
6. `Rol.md`, `prompts.md`, `promptsWeb.md` y `guides.md`: material operativo o de referencia, nunca autoridad superior.

Si existe un conflicto no resuelto sobre seguridad, integridad de datos o comportamiento, **no improvises**: detén el avance y solicita la decisión necesaria.

## Proyecto
Apply: bot que busca ofertas de trabajo en muchas fuentes (job boards, APIs públicas, foros, grupos y publicaciones con hashtags de contratación), las filtra contra el CV de `cvs/profile.json` (nivel junior/mid, remoto, geografía permitida, español o inglés hasta B2, sin estafas ni empresas bloqueadas), genera cartas de presentación y envía un reporte diario por correo. En fases posteriores podrá postular de forma asistida/automática (ver `specs/003-postulacion-automatica`).

Stack: Python 3.11+; requests + BeautifulSoup4 (scraping), pymongo (persistencia opcional), praw (Reddit), playwright (postulación, fase 003), pytest + ruff (verificación).
Estructura: código en `src/`, tests en `tests/`, specs en `specs/`.

## Comandos
- Ejecutar: `python -m src.main`
- Tests: `python -m pytest`
- Lint/formato: `python -m ruff check src tests`

## Clasificación del trabajo

Antes de editar, identifica el tipo de cambio:

- **Nueva funcionalidad / cambio de comportamiento:** requiere RF aprobado en la spec.
- **Bug o regresión:** primero reproduce, identifica causa raíz y corrige el comportamiento ya definido. Si la spec no representa el comportamiento correcto, actualízala antes o como parte del cambio aprobado.
- **Refactor:** no debe cambiar comportamiento; requiere evidencia de que el contrato existente se conserva.
- **Docs, configuración, infraestructura o tooling:** pueden no tener RF, pero deben estar justificados por una tarea, decisión técnica o requisito no funcional aprobado.

La trazabilidad debe cubrir todo cambio de comportamiento; no debe usarse el RF como excusa para exigirlo a cada archivo de soporte.

## Reglas obligatorias

- Inspecciona el repositorio antes de editar.
- Lee la constitución y la spec/plan activos antes de tocar código relacionado.
- No inventes requisitos, reglas de negocio, permisos, contratos API, decisiones de seguridad o datos.
- Si falta una decisión que cambia comportamiento o arquitectura, usa `[NECESITA DECISIÓN]` y detente en ese punto.
- Una suposición solo puede usarse si el usuario la autorizó explícitamente o una regla aprobada ya la define; debe quedar documentada y aislada.
- Haz el cambio más pequeño y reversible que resuelva la causa raíz.
- Preserva el comportamiento no relacionado con la tarea.
- No añadas dependencias, abstracciones, UI o efectos solo para que el proyecto parezca más completo o moderno.

## Verificación

Después de un cambio, ejecuta la verificación apropiada al tipo de trabajo:

- Código de comportamiento: tests relevantes y suite completa cuando esté configurada.
- Tipos/lint/build: ejecutar los checks configurados cuando el cambio los pueda afectar.
- UI: comprobar estados, rutas, responsive y accesibilidad aplicables.
- Docs/config: validar sintaxis, referencias y el mecanismo afectado.

No marques una tarea como terminada ni afirmes que algo está verificado sin evidencia.

## Aprobación y delegación

Por defecto, cada fase de SDD requiere aprobación humana antes de avanzar.

Una vez que el usuario aprueba un plan o autoriza explícitamente un rango de tareas, el agente puede ejecutar ese rango sin detenerse después de cada tarea, siempre que:

- no cambie el alcance aprobado;
- no aparezca una decisión bloqueante;
- las verificaciones sigan pasando;
- no se introduzca una regresión conocida.

Si aparece una decisión nueva o un conflicto, detente aunque exista delegación previa.

## Al terminar

Reporta:
- qué cambió;
- qué requisito, tarea o decisión cubre;
- verificación ejecutada y resultado;
- riesgos o decisiones pendientes;
- siguiente paso, solo si corresponde.

PÁRATE cuando el alcance aprobado haya terminado.
