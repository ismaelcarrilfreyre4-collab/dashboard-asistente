# 🎙️ Asistente de Voz — Dashboard Web

Dashboard web moderno y unificado para el monitoreo y visualización del **Asistente de Voz**. Integra backend en **FastAPI**, orquestación de flujos en **n8n**, transcripción con **Groq (Whisper)**, resumen/clasificación con **LM Studio (Qwen2.5-3B)**, sincronización con **Todoist** y almacenamiento en **Notion**.

---

## 🏗️ Arquitectura del Sistema

```text
  [ Usuario (Telegram) ]
            │ (Audio / Texto)
            ▼
    [ Webhook n8n ] (http://localhost:5678)
            │
            ├──► 1. Renombrar .oga a .ogg
            ├──► 2. Groq Whisper (Transcripción STT)
            ├──► 3. LM Studio Qwen2.5-3B (Resumen & Clasificación: Idea/Tarea/Recordatorio)
            ├──► 4. Todoist API (Creación de tareas con etiqueta)
            ├──► 5. Notion API (Páginas con resumen, categoría, fecha, transcripción)
            └──► 6. Telegram Bot (Respuesta al usuario)
            │
            ▼
┌─────────────────────────────────────────────────────────────┐
│              DASHBOARD WEB (FastAPI + HTML)                 │
│                 http://localhost:8000/                      │
│                                                             │
│  • Conteo en vivo (Ideas, Tareas, Recordatorios)           │
│  • Feed de últimas 20 notas desde Notion                   │
│  • Monitor de salud de los 5 servicios en tiempo real       │
│  • Estado y pipeline del orquestador n8n                   │
│  • Fallback automático Mock ↔ Real según variables .env    │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎨 Vista Previa del Dashboard (ASCII Art)

```text
+-------------------------------------------------------------------------------------------------+
| 🎙️ Asistente de Voz · Dashboard           [● Modo Mock (Datos de prueba)]  [Auto: 30s] [🔄 Actualizar] |
| Martes, 6 de octubre de 2026                                                                    |
+-------------------------------------------------------------------------------------------------+
| 📊 MÉTRICAS DE CAPTURA                                                     Total: 25 elementos  |
| +-------------------------+ +-------------------------+ +-------------------------------------+ |
| | 💡 IDEAS                | | ✅ TAREAS               | | ⏰ RECORDATORIOS                    | |
| |        12               | |         8               | |          5                          | |
| | Conceptos y proyectos   | | Acciones en Todoist     | | Avisos y citas                      | |
| +-------------------------+ +-------------------------+ +-------------------------------------+ |
+-------------------------------------------------------------------------------------------------+
| 📝 ÚLTIMAS NOTAS PROCESADAS              [Todas] [💡 Ideas] [✅ Tareas] [⏰ Recordatorios]      |
| +---------------------------------------------------------+ +---------------------------------+ |
| | [ 💡 Idea ]                     📅 6 de octubre, 12:00  | | 🔌 ESTADO DE SERVICIOS   5/5 Activos| |
| | App de recetas con IA                                   | | • ⚡ n8n Orquestador        [✓ Online] | |
| | Idea: app que sugiere recetas según ingredientes...     | | • 🧠 LM Studio (Qwen2.5)    [✓ Online] | |
| | 🎙️ Transcripción: "Se me ocurrió una app..."             | | • 🎙️ Groq (Whisper)         [✓ Online] | |
| +---------------------------------------------------------+ | • ✅ Todoist                [✓ Online] | |
| | [ ✅ Tarea ]                    📅 5 de octubre, 09:30  | | • 📓 Notion                 [✓ Online] | |
| | Enviar informe al cliente                               | | ℹ️ n8n y LM Studio corren en la | |
| | Tarea: enviar el informe mensual antes del viernes...   | |    PC de Alex. Dashboard solo lee. | |
| +---------------------------------------------------------+ +---------------------------------+ |
| | [ ⏰ Recordatorio ]             📅 4 de octubre, 16:15  | | ⚙️ FLUJO N8N             [ Online ] | |
| | Comprar pan mañana                                      | | 1️⃣ Recibe Telegram               | |
| | Recordatorio de comprar pan al salir de la oficina...   | | 2️⃣ Transcribe con Groq (Whisper) | |
| +---------------------------------------------------------+ | 3️⃣ Clasifica con LM Studio       | |
|                                                           | | 4️⃣ Guarda en Todoist y Notion     | |
|                                                           | | 5️⃣ Responde por Telegram        | |
|                                                           | | [ 🔗 Abrir n8n (localhost:5678) ] | |
|                                                           | +---------------------------------+ |
+-------------------------------------------------------------------------------------------------+
```

---

## 📁 Estructura del Proyecto

```text
dashboard-asistente/
├── backend/
│   ├── main.py              # FastAPI: endpoints de API, healthcheck y sirve el frontend
│   ├── todoist_client.py    # Cliente asíncrono para Todoist (con fallback Mock)
│   ├── notion_client.py     # Cliente asíncrono para Notion (con fallback Mock)
│   ├── requirements.txt     # Dependencias de Python
│   ├── .env.example         # Plantilla de variables de entorno
│   ├── .env                 # Variables de entorno locales (ignorado en git)
│   └── README.md            # Documentación específica del backend
├── frontend/
│   └── index.html           # Dashboard completo responsive (Tailwind CSS CDN + Vanilla JS)
├── .gitignore               # Exclusiones de Git (entornos, caches, .env)
└── README.md                # Documentación general del proyecto
```

---

## 🚀 Inicio Rápido (Backend + Frontend en 1 Comando)

### Prerrequisitos
- Python 3.10 o superior instalado.

### 1. Instalar dependencias (primera vez)
```powershell
# En Windows PowerShell desde la raíz del proyecto:
pip install -r backend/requirements.txt
```

### 2. Ejecutar el servidor
Puedes iniciar el backend (que a su vez sirve automáticamente el frontend) con este único comando:

```powershell
uvicorn backend.main:app --reload --port 8000
```
*(O si estás dentro de la carpeta `backend`)*:
```powershell
cd backend
uvicorn main:app --reload --port 8000
```

### 3. Abrir en el navegador
Visita en tu navegador web:
👉 **`http://localhost:8000/`**

---

## 🔍 Cómo Verificar que Todo Funciona

### 1. Comprobación del Frontend
- Al abrir `http://localhost:8000/` verás el dashboard en modo oscuro.
- Si las variables de `.env` están vacías, la cabecera mostrará el badge **`Modo Mock (Datos de prueba)`**.
- Las 3 tarjetas de estadísticas mostrarán los números mock (`12`, `8`, `5`).
- La lista de notas mostrará 5 notas de prueba clasificadas con sus etiquetas correspondientes.
- Puedes probar los botones de filtrado (`Todas`, `💡 Ideas`, `✅ Tareas`, `⏰ Recordatorios`).
- El botón **🔄 Actualizar** recargará las métricas y el contador regresivo de **30s** gestionará el auto-refresh.

### 2. Comprobación de Endpoints (vía cURL o navegador)

| Endpoint | Método | Descripción | Respuesta esperada |
|---|---|---|---|
| `/` | `GET` | Dashboard web | HTML del frontend |
| `/health` | `GET` | Verificación de salud | `{"status": "ok"}` |
| `/api/stats` | `GET` | Conteo de categorías | `{"ideas": 12, "tareas": 8, "recordatorios": 5, "total": 25}` |
| `/api/notas?limit=5` | `GET` | Últimas notas de Notion | `{"notas": [...]}` |
| `/api/estado` | `GET` | Estado de servicios y modo | `{"n8n": bool, "lm_studio": bool, "groq": bool, "todoist": bool, "notion": bool, "modo": "mock"\|"real"}` |
| `/api/n8n-info` | `GET` | Metadatos y pipeline de n8n | `{"url": "...", "estado": "online"\|"offline", "descripcion": "...", "responsabilidades": [...]}` |

Pruebas en terminal:
```powershell
curl http://localhost:8000/health
curl http://localhost:8000/api/stats
curl "http://localhost:8000/api/notas?limit=5"
curl http://localhost:8000/api/estado
curl http://localhost:8000/api/n8n-info
```

Documentación interactiva Swagger:
👉 **`http://localhost:8000/docs`**

---

## 🔑 Conectar Datos Reales (Instrucciones para Alex)

El dashboard está programado con **fallback transparente**: no requiere tokens para funcionar durante el desarrollo, pero se conectará a las APIs reales inmediatamente cuando se agreguen las credenciales en `backend/.env`.

### Pasos para Alex:

1. **Crear o editar `backend/.env`**:
   Copia el archivo `backend/.env.example` a `backend/.env` (si aún no existe) y completa los siguientes campos:

   ```env
   # --- Credenciales principales ---
   TODOIST_API_TOKEN=tu_token_de_todoist
   NOTION_API_TOKEN=secret_tu_integration_token_de_notion
   NOTION_DATABASE_ID=tu_database_id_de_notion_32_caracteres
   GROQ_API_KEY=gsk_tu_api_key_de_groq

   # --- URLs de servicios locales de Alex (opcionales, tienen valores por defecto) ---
   N8N_URL=http://localhost:5678
   LM_STUDIO_URL=http://192.168.56.1:1234
   ```

2. **Detalles para obtener cada credencial**:
   - **Todoist**:
     - Ve a *Ajustes de Todoist* → *Integraciones* → pestaña *Desarrollador* → copia el **API token**.
     - Las etiquetas que asigna n8n deben llamarse exactamente `Idea`, `Tarea` y `Recordatorio`.
   - **Notion**:
     - Ve a [notion.so/my-integrations](https://www.notion.so/my-integrations) → Crea una integración y copia el **Internal Integration Secret**.
     - Abre la base de datos "Notas de Voz" en Notion → Menú de tres puntos `•••` (arriba a la derecha) → **Conexiones** → Añade la integración creada (imprescindible para evitar error 404).
     - Copia el `NOTION_DATABASE_ID`: son los 32 caracteres alfanuméricos de la URL de la base de datos antes del `?v=`.
   - **Groq**:
     - Consola de desarrollador en [console.groq.com/keys](https://console.groq.com/keys).
   - **LM Studio**:
     - Verifica que el servidor local de LM Studio esté encendido en `http://192.168.56.1:1234` con el modelo `Qwen2.5-3B` cargado.

3. **Reiniciar el backend**:
   Detén la terminal con `Ctrl + C` y vuelve a ejecutar:
   ```powershell
   uvicorn backend.main:app --reload --port 8000
   ```

4. **Verificación**:
   Recarga `http://localhost:8000/`. El indicador superior cambiará de **Modo Mock** a **Modo Real (APIs Conectadas)** con un indicador verde pulsante.
