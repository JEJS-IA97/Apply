# Apply — metodología SDD

Este proyecto sigue **Spec-Driven Development (SDD)**: la especificación manda sobre el código, y ningún comportamiento se implementa sin estar definido y aprobado antes. Esta es la copia aplicada de la base `projects-base` para este repositorio.

---

## ¿Qué es SDD y por qué lo usamos?

**Vibe coding** es pedirle a una IA "hazme una app de X" y aceptar lo que devuelva. Funciona para prototipos, pero produce código imposible de mantener, sin tests, con decisiones no documentadas y errores difíciles de localizar.

**Spec-Driven Development (SDD)** invierte el orden: primero se define **el qué y el por qué** (spec), luego **el cómo** (plan), después **las tareas** (tasks) y solo al final **el código**. Cada fase tiene un prompt específico y un artefacto verificable. Beneficios:

- **Trazabilidad:** cada línea de código existe porque un requisito (RF) la justifica.
- **Auditabilidad:** se sabe qué se pidió, qué se decidió y por qué.
- **Robustez:** los tests son la puerta de entrada; no se avanza con tests en rojo.
- **Mantenibilidad:** el contexto está en archivos, no en la cabeza de nadie.
- **IA controlada:** el agente sigue reglas fijas, no improvisa.

---

## Flujo de trabajo SDD (7 fases)

| # | Fase | Entrada | Salida | Prompt |
|---|------|---------|--------|--------|
| 1 | Constitución | Idea del proyecto | `docs/constitution.md` | Ver `prompts.md` |
| 2 | Spec | Constitución + idea | `specs/NNN-*/spec.md` | Ver `prompts.md` |
| 3 | Clarificación | Spec | Spec revisada por QA | Ver `prompts.md` |
| 4 | Plan | Spec + constitución | `specs/NNN-*/plan.md` | Ver `prompts.md` |
| 5 | Tareas | Plan | `specs/NNN-*/tasks.md` | Ver `prompts.md` |
| 6 | Implementación | Tareas | Código + tests | Ver `prompts.md` |
| 7 | Validación | Spec + código | Veredicto RF por RF | Ver `prompts.md` |

**Regla de oro:** cada fase espera aprobación humana antes de pasar a la siguiente.

---

## Cómo trabajar en este proyecto

1. La base ya está aplicada en este repositorio (`AGENTS.md`, `docs/`, `specs/`, `prompts.md`).
2. Toda funcionalidad o cambio de comportamiento nuevo pasa por: spec → clarificación → plan → tareas → implementación → validación.
3. Los prompts de cada fase están en `prompts.md`; el contrato operativo del agente está en `AGENTS.md`.
4. La jerarquía de autoridad está definida en `AGENTS.md` (usuario > constitución > spec/plan > AGENTS.md > guías).
5. Estado actual de las specs: ver `specs/`.

## Specs activas

| Spec | Estado |
|------|--------|
| `specs/001-filtrado-nivel-confianza-idioma` | Ajuste de filtrado (nivel, confianza/estafas, idioma) |
| `specs/002-fuentes-posts-foros-grupos` | Ampliación de fuentes (posts, foros, grupos, hashtags) |
| `specs/003-postulacion-automatica` | Postulación asistida/automática (pendiente de decisión) |
