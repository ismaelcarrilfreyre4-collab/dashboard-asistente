# Dashboard del Asistente de Voz — Backend

API en FastAPI que funciona **desde el primer minuto con datos de ejemplo (mock)** y se conecta
a Todoist y Notion reales automáticamente cuando el `.env` tiene los tokens.

## Instalación
```bash
cd dashboard/backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # Windows: copy .env.example .env
```

## Ejecutar
```bash
uvicorn main:app --reload --port 8000
```
Docs interactivas: http://localhost:8000/docs
Si existe `dashboard/frontend/index.html`, se sirve en http://localhost:8000/

## Probar
```bash
curl http://localhost:8000/api/stats
curl "http://localhost:8000/api/notas?limit=5"
curl http://localhost:8000/api/estado
```

## Cómo funciona mock / real

| Endpoint | Sin credenciales | Con credenciales |
|---|---|---|
| `/api/stats` | 12 / 8 / 5 / 25 | Cuenta tareas reales de Todoist por etiqueta |
| `/api/notas` | 5 notas de ejemplo | Lee la base de datos real de Notion |
| `/api/estado` | n8n y LM Studio se comprueban de verdad; Groq, Todoist y Notion = `false` | Se comprueban todos |

- El campo `modo` de `/api/estado` vale `"mock"` (sin tokens), `"real"` (Todoist y Notion configurados) o `"mixto"` (solo uno de los dos).
- Si hay token pero la API falla (token inválido, sin red...), el endpoint devuelve datos mock y deja el motivo en la consola.
- El `.env` se lee al arrancar el servidor: **reinicia uvicorn tras cambiarlo** (el modo `--reload` solo reinicia al cambiar archivos `.py`).

## Para conectar datos reales (instrucciones para Alex)

1. **Rellenar el `.env`** (en `dashboard/backend/`, copiado de `.env.example`):
   ```
   TODOIST_API_TOKEN=tu_token_de_todoist
   NOTION_API_TOKEN=tu_integration_token_de_notion
   NOTION_DATABASE_ID=id_de_la_base_de_datos_notas_de_voz
   GROQ_API_KEY=tu_api_key_de_groq
   ```
   - Todoist: Ajustes → Integraciones → Desarrollador → API token.
   - Notion: https://www.notion.so/my-integrations → copia el *Internal Integration Secret*. Luego abre la base de datos "Notas de Voz" → ••• → Conexiones → añade la integración (si no, Notion devuelve 404).
   - `NOTION_DATABASE_ID`: los 32 caracteres de la URL de la base de datos, antes del `?v=`.
   - Groq: https://console.groq.com/keys
2. **Reiniciar el servidor**: `Ctrl+C` y de nuevo `uvicorn main:app --reload --port 8000`.
3. **Listo**: el dashboard leerá datos reales automáticamente. Comprueba `curl http://localhost:8000/api/estado` y verifica que `"modo"` ya no sea `"mock"`.

## Notas
- Las etiquetas de Todoist deben llamarse `Idea`, `Tarea` y `Recordatorio`. Solo cuentan tareas activas (las completadas no aparecen en la API).
- Todoist está migrando de REST v2 a la API v1. Si `todoist` sale en `false` con un token válido, añade al `.env`: `TODOIST_BASE_URL=https://api.todoist.com/api/v1`.
- Las columnas de Notion esperadas: título, `Resumen`, `Categoría` (Selección), `Fecha` (Date), `Transcripción`.
