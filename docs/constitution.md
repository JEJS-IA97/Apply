# Constitución del proyecto — Apply

> **Estado:** BORRADOR. Debe aprobarse antes de implementar cambios de comportamiento derivados de las specs activas.

## Propósito

Definir los principios específicos que gobiernan este proyecto: producto, arquitectura, calidad, seguridad, pruebas, datos y límites éticos.

## Reglas de esta plantilla

1. La constitución, la spec activa y el plan aprobado son la fuente de verdad del proyecto.
2. El agente no inventará requisitos, contratos, permisos, reglas de negocio ni decisiones de seguridad.
3. Una decisión faltante que cambie comportamiento o arquitectura debe quedar como `[NECESITA DECISIÓN]` y detener el avance en ese punto.
4. Las suposiciones solo son válidas cuando el usuario las autoriza explícitamente o cuando una regla del proyecto ya las define; deben quedar documentadas y aisladas.
5. Los cambios de comportamiento deben ser trazables a requisitos aprobados y verificables.
6. Las tareas de documentación, configuración, infraestructura, tests o mantenimiento pueden justificarse por una decisión técnica o tarea aprobada aunque no introduzcan un RF.
7. El agente preservará comportamiento existente no relacionado con la tarea y preferirá cambios pequeños y reversibles.
8. Ninguna afirmación de "hecho", "verificado", "seguro", "optimizado" o "funciona" se hará sin evidencia correspondiente.

## Principios del proyecto

- **P1 — Solo ofertas que el usuario pueda ejercer.** Nivel junior/mid (o sin nivel explícito), remoto, geografía permitida, idioma español o inglés hasta B2. Nada de ofertas senior/staff/director ni de regiones bloqueadas.
- **P2 — Cero estafas.** Se excluyen empresas, marcas y patrones de scam conocidos (cobros por postular, "gana X semana", pagos iniciales, captación por WhatsApp/IA falsa). Una oferta dudosa se descarta, no se "arregla".
- **P3 — Ética y legalidad en la recolección.** Solo fuentes públicas, APIs permitidas o credenciales propias del usuario. Sin eludir CAPTCHAs/bloqueos, con rate limiting y user-agent identificable, respetando términos de servicio razonables. Nueva fuente = RF aprobado.
- **P4 — Transparencia y trazabilidad.** Cada filtrado es configurable (perfil/config, no hardcodeado) y registra el motivo. El reporte diario refleja exactamente lo que pasó los filtros.
- **P5 — Control humano sobre las postulaciones.** Ninguna postulación automática se envía sin RF aprobado, límite de envíos y registro de cada envío. El usuario puede pausar el modo automático.
- **P6 — Sin datos inventados.** No se fabrican empresas, salarios, requisitos ni testimonios; la IA solo se usa si la spec lo autoriza y su salida se marca como tal.
- **P7 — Verificación obligatoria.** Todo cambio de comportamiento se verifica con tests o evidencia reproducible antes de declararlo terminado.
- **P8 — Cambios mínimos.** Prevalece el cambio más pequeño y reversible que resuelva la causa raíz; sin dependencias, abstracciones ni efectos decorativos.

## Decisiones y excepciones

- [2026-10-06] — Se adopta la base `projects-base` (SDD) sobre el código existente — el proyecto ya tiene MVP funcional pero sin specs — alcance: gobernanza del repo.
- [2026-10-06] — Los PDF del CV en `cvs/` NO se trackean (`*.pdf` en `.gitignore`); la fuente versionada del perfil es `cvs/profile.json` — los PDF son datos sensibles locales — alcance: `cvs/`.

## Aprobación

- Estado: [BORRADOR]
- Fecha: [pendiente]
