# Prompts por fase SDD

Los prompts son interfaces de trabajo; no sustituyen la jerarquía de `AGENTS.md`. **No saltes fases**, salvo que el usuario autorice explícitamente un flujo distinto.

| Fase | Prompt esencial |
|------|-----------------|
| **Constitución** | “Proponme la constitución de este proyecto: N principios cortos y verificables sobre producto, arquitectura, calidad, seguridad, tests y límites. Máx. 15 líneas. No escribas código. Espera mi aprobación.” |
| **Research (apoyo)** | “Investiga solo lo necesario para resolver la pregunta. Prioriza fuentes primarias/oficiales, registra fecha de consulta, evidencia, incertidumbres y enlaces. No diseñes la solución ni modifiques código.” |
| **Spec (entrevista)** | “NO escribas código. Haz preguntas sobre alcance, casos límite, errores, permisos y criterios de aceptación. Después genera `spec.md` con RF numerados en EARS, RNF, fuera de alcance y criterios de finalización. Solo QUÉ y POR QUÉ.” |
| **Clarificación** | “Revisa la spec como QA profesional: ambigüedades, contradicciones, casos límite ausentes, riesgos y conflictos con la constitución. Solo detecta; no resuelvas decisiones sin aprobación.” |
| **Plan** | “Lee constitución y spec. Sin código: genera `plan.md` con módulos, modelo de datos, decisiones justificadas, alternativas descartadas, riesgos y estrategia de tests. Mapea cada RF.” |
| **Tareas** | “Divide el plan en tareas pequeñas y ordenadas por dependencia. Cada tarea debe incluir su RF, RNF o decisión técnica, criterio ‘Hecho cuando:’ y verificación. Marca checkboxes.” |
| **Implementación** | “Implementa SOLO el alcance aprobado. Inspecciona antes de editar, prueba la causa raíz, haz el cambio mínimo seguro y verifica. No amplíes el alcance silenciosamente.” |
| **Validación** | “Recorre la spec RF por RF y RNF por RNF: evidencia, test/verification y resultado. Distingue cumplido, no cumplido y no verificable. No declares éxito sin evidencia.” |
| **Cambio** | “Nuevo requisito: {{descripción}}. No toques código. Propón el cambio a spec/plan, su impacto y el diff conceptual. Espera aprobación.” |

## Reglas de uso

1. Un prompt corresponde a una fase.
2. La investigación es una actividad de apoyo, no una fase que autoriza implementación.
3. Una aprobación de un plan puede delegar varias tareas; el agente debe respetar los límites aprobados.
4. Si falta una decisión que cambie comportamiento o arquitectura, se detiene el avance en ese punto.
5. No se exige un RF para cada archivo de soporte: se exige trazabilidad para cada cambio de comportamiento.
6. Para docs, configuración, infraestructura y refactors, usa la verificación apropiada al cambio.
