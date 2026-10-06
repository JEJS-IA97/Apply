# Cambios pendientes en documentos grandes

## ANTI_VIBECODE_GUIDE.md

1. En `## 1.3 Do not invent product requirements`, reemplaza:

> When requirements are missing, use the smallest reasonable assumption and isolate it so it can be changed later. Do not spread invented assumptions through the application.

por:

> When a missing decision can change behavior, architecture, security, permissions, data integrity or public API contracts, do not guess. Mark it as `[NEEDS DECISION]`, isolate the blocked work and ask for the decision. An assumption is allowed only when the user explicitly delegates that decision or an approved project rule already defines it; document the assumption and its scope.

2. Añade cerca del inicio, después de `## 0. Core objective`, una sección de gobierno equivalente a:

> ## 0.1 Governance and applicability
> This document is a reusable engineering standard, not the project's source of truth. `AGENTS.md`, the approved constitution, and the active spec/plan define project-specific behavior. This standard supplies guardrails where the project documents are silent. It must not override an explicit approved project decision.
>
> Traceability applies primarily to behavior and contract changes. Supporting code, tests, docs, configuration and infrastructure may be justified by an approved task, non-functional requirement or technical decision without inventing an RF for every file.

3. En cualquier lugar donde se sugiera asumir por defecto, sustituir por la misma política de `NEEDS DECISION`.

4. Donde se diga que todo debe tener un RF, aclarar: **todo cambio de comportamiento** debe tener requisito/decisión aprobada; no cada archivo de soporte.

5. Mantener las reglas visuales como heurísticas anti-slop, no como prohibiciones absolutas. La guía ya lo expresa bien en `1.1`; conservar ese criterio.

6. Mantener SEO condicionado a páginas públicas indexables. No convertir una recomendación web en requisito para apps privadas/mobile.

## ANTI_VIBECODE_PROMPT.md

1. Añadir arriba una sección de jerarquía que indique que `AGENTS.md` + constitución + spec/plan aprobados tienen prioridad.
2. Reemplazar la política de “smallest reasonable assumption” por `NEEDS DECISION`.
3. Añadir la clasificación de trabajo: feature, bugfix, refactor, docs/config/tooling.
4. Cambiar “tests first” de una obligación mecánica para todo a una regla de verificación apropiada al tipo de cambio; mantener TDD como preferencia fuerte para lógica y comportamiento crítico.
5. Añadir una regla: una aprobación puede delegar un rango de tareas; no debe ser necesario detenerse después de cada task si el alcance ya fue aprobado.

## ANTI_VIBECODE_STANDARD.json

Añadir estas claves al nivel raíz:

```json
"governance": {
  "instruction_precedence": [
    "user-approved-scope",
    "approved-constitution",
    "active-approved-spec-and-plan",
    "AGENTS.md",
    "ANTI_VIBECODE_GUIDE.md",
    "ANTI_VIBECODE_STANDARD.json",
    "role-and-reference-prompts"
  ],
  "missing_decision": "stop_and_request_decision_when_behavior_architecture_security_permissions_data_integrity_or_public_contracts_are_affected",
  "explicit_assumptions_only": true,
  "traceability_scope": "behavior_and_contract_changes",
  "supporting_work_may_map_to": ["non_functional_requirement", "approved_task", "technical_decision"]
},
"research": {
  "read_only": true,
  "primary_sources_preferred": true,
  "must_record_date_for_current_information": true,
  "distinguish_fact_inference_recommendation": true,
  "must_not_modify_repository": true
}
```

Cambiar además el `agent_instruction` para decir que el estándar es un guardrail, que no inventa decisiones y que la trazabilidad es para cambios de comportamiento/contratos, no para cada archivo.

## specs/001-{{nombre-feature-mvp}}/spec.md

Cambiar:

> No hay código sin RF que lo justifique.

por:

> Todo cambio de comportamiento o contrato está justificado por un RF/RNF/decisión aprobada. El código de soporte, tests, configuración o infraestructura puede estar justificado por una tarea o decisión técnica aprobada.
