# Agente de investigación

## Objetivo

Añadir una capa de investigación actual al flujo de desarrollo sin convertir al modelo investigador en el encargado de programar.

La investigación debe responder preguntas como:

- ¿Cuál es la API/versión correcta hoy?
- ¿Qué cambió en una librería/framework?
- ¿Existe una vulnerabilidad o breaking change conocido?
- ¿Qué recomienda la documentación oficial para un caso concreto?
- ¿Qué alternativas existen y qué trade-offs tienen?
- ¿Qué restricciones actuales de una plataforma pueden afectar el diseño?

El researcher entrega evidencia al agente constructor. El constructor decide si esa evidencia justifica un cambio, y cualquier cambio de comportamiento sigue pasando por spec/plan/aprobación.

## Integración recomendada con OpenCode

OpenCode permite subagentes definidos en `.opencode/agents/` y permite controlar sus permisos. El researcher incluido aquí no tiene permisos de edición ni shell; solo investigación web.

En la documentación actual de OpenCode, `websearch` y `webfetch` están disponibles como herramientas de investigación; `websearch` no requiere una API key propia cuando se habilita mediante la infraestructura compatible de OpenCode. Para activarlo al iniciar OpenCode en PowerShell:

```powershell
$env:OPENCODE_ENABLE_EXA="1"
opencode
```

Después puede invocarse manualmente con:

```text
@researcher investiga ...
```

## Google Gemini API: uso opcional

No recomiendo convertir Gemini en el agente programador. Puede ser útil como **fuente adicional de investigación**, especialmente para grounding con Google Search.

A fecha de 2026-10-06, la documentación de Gemini indica que ciertos modelos tienen cuota gratuita de entrada/salida y que Gemini 2.5 Flash-Lite dispone de grounding con Google Search gratuito de hasta 500 solicitudes diarias en el nivel gratuito. La cuota depende del proyecto/modelo y puede cambiar.

La capa gratuita también indica que el contenido puede utilizarse para mejorar productos de Google. Por eso, para repositorios privados o información sensible, el researcher no debe enviar automáticamente el código completo ni secretos a Gemini.

La API key debe vivir fuera del repositorio, por ejemplo en `GEMINI_API_KEY`, y nunca en código, `VITE_*`, prompts versionados o commits.

## Decisión recomendada

Para esta base reutilizable, deja **OpenCode + websearch/webfetch** como camino por defecto: es más simple, no introduce una credencial obligatoria y mantiene el sistema agnóstico del proveedor.

Añade Gemini solo como integración opcional cuando realmente aporte una ventaja verificable de cobertura o grounding con Google Search.
