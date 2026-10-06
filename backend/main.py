"""
Backend del dashboard del asistente de voz (con modo MOCK / REAL).

Endpoints:
    GET /                   -> sirve frontend/index.html
    GET /health             -> estado de vida {"status": "ok"}
    GET /api/stats          -> conteo de Ideas / Tareas / Recordatorios
    GET /api/notas?limit=20 -> últimas notas de Notion
    GET /api/estado         -> estado de los servicios + modo (mock / real / mixto)
    GET /api/n8n-info       -> información y estado del orquestador n8n

Lógica mock/real: se decide en cada petición según el .env.
Sin tokens -> datos de ejemplo. Con tokens -> APIs reales.
Ejecutar:  uvicorn main:app --reload --port 8000
"""
import asyncio
import logging
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# Asegurar que el directorio backend esté en sys.path independientemente de dónde se ejecute uvicorn
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

load_dotenv(BACKEND_DIR / ".env")  # cargar .env del backend explícitamente

import notion_client  # noqa: E402
import todoist_client  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dashboard")

app = FastAPI(title="Dashboard Asistente de Voz", version="1.0.0")

# CORS abierto: permite consumir la API desde cualquier origen (localhost:3000, file://, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rutas del frontend
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
INDEX_HTML = FRONTEND_DIR / "index.html"


def modo_actual() -> str:
    """
    "mock"  -> no hay credenciales de Todoist ni de Notion
    "real"  -> hay credenciales de ambos
    "mixto" -> solo de uno de los dos (el otro devuelve datos mock)
    """
    todoist, notion = todoist_client.configurado(), notion_client.configurado()
    if todoist and notion:
        return "real"
    if todoist or notion:
        return "mixto"
    return "mock"


# ------------------------------------------------------------------ Health check
@app.get("/health")
async def health():
    """Comprobación de salud básica para monitoreo."""
    return {"status": "ok"}


# ----------------------------------------------------------------- /api/stats
@app.get("/api/stats")
async def stats():
    """Conteo por categoría: Todoist real si hay token; si no, mock."""
    try:
        return await todoist_client.contar_por_categoria()
    except Exception as exc:  # red de seguridad final
        logger.error("Error en /api/stats: %s", exc)
        return dict(todoist_client.MOCK_STATS)


# ----------------------------------------------------------------- /api/notas
@app.get("/api/notas")
async def notas(limit: int = Query(20, ge=1, le=100)):
    """Últimas notas: Notion real si hay credenciales; si no, mock."""
    try:
        return {"notas": await notion_client.listar_notas(limit)}
    except Exception as exc:
        logger.error("Error en /api/notas: %s", exc)
        return {"notas": notion_client.notas_mock(limit)}


# ---------------------------------------------------------------- /api/estado
async def _ping(client: httpx.AsyncClient, url: str, headers: dict | None = None) -> bool:
    """True si la URL responde con HTTP 200."""
    try:
        resp = await client.get(url, headers=headers or {})
        return resp.status_code == 200
    except (httpx.HTTPError, Exception):
        return False


async def _siempre_false() -> bool:
    """Para servicios que necesitan token y no lo tienen."""
    return False


@app.get("/api/estado")
async def estado():
    """Comprueba en paralelo cada servicio. Sin token -> false (n8n y LM Studio no lo necesitan)."""
    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            n8n, lm, groq, todoist, notion = await asyncio.gather(
                _ping(client, os.getenv("N8N_URL", "http://localhost:5678").rstrip("/") + "/healthz"),
                _ping(client, os.getenv("LM_STUDIO_URL", "http://192.168.56.1:1234").rstrip("/") + "/v1/models"),
                _ping(
                    client,
                    "https://api.groq.com/openai/v1/models",
                    {"Authorization": f"Bearer {groq_key}"},
                )
                if groq_key
                else _siempre_false(),
                _ping(client, f"{todoist_client.base_url()}/projects", todoist_client.headers())
                if todoist_client.configurado()
                else _siempre_false(),
                _ping(client, "https://api.notion.com/v1/users/me", notion_client.headers())
                if os.getenv("NOTION_API_TOKEN", "").strip()
                else _siempre_false(),
            )
        resultado = {
            "n8n": n8n,
            "lm_studio": lm,
            "groq": groq,
            "todoist": todoist,
            "notion": notion,
        }
    except Exception as exc:
        logger.error("Error en /api/estado: %s", exc)
        resultado = {
            "n8n": False,
            "lm_studio": False,
            "groq": False,
            "todoist": False,
            "notion": False,
        }

    resultado["modo"] = modo_actual()
    return resultado


# -------------------------------------------------------------- /api/n8n-info
@app.get("/api/n8n-info")
async def n8n_info():
    """Devuelve metadatos del workflow de n8n y comprueba su estado online/offline."""
    n8n_url = os.getenv("N8N_URL", "http://localhost:5678").strip().rstrip("/")
    online = False
    try:
        async with httpx.AsyncClient(timeout=2) as client:
            online = await _ping(client, f"{n8n_url}/healthz")
    except Exception as exc:
        logger.debug("Error comprobando n8n en %s: %s", n8n_url, exc)
        online = False

    return {
        "url": n8n_url,
        "estado": "online" if online else "offline",
        "descripcion": "Orquestador del asistente de voz",
        "responsabilidades": [
            "Recibe audios y textos de Telegram",
            "Transcribe con Groq (Whisper)",
            "Resume y clasifica con LM Studio (Qwen2.5)",
            "Guarda en Todoist y Notion",
            "Responde al usuario por Telegram",
        ],
    }


# ----------------------------------------------------------- Frontend & Estáticos
@app.get("/")
@app.get("/index.html")
async def root():
    """Sirve la interfaz web del dashboard."""
    if INDEX_HTML.is_file():
        return FileResponse(INDEX_HTML)
    return JSONResponse(
        status_code=404,
        content={
            "error": "Archivo frontend/index.html no encontrado.",
            "detalle": f"Verifique que exista el archivo en {INDEX_HTML}",
        },
    )


# Montar carpeta frontend como estáticos si existe (para favicon, css, js o assets)
if FRONTEND_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
