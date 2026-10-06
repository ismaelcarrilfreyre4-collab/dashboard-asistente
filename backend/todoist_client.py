"""
Cliente asíncrono de Todoist con fallback a datos MOCK.

Regla:
  - Sin TODOIST_API_TOKEN en el .env  -> devuelve MOCK_STATS
  - Con token                         -> cuenta tareas reales por etiqueta
  - Con token pero la API falla       -> devuelve MOCK_STATS (y lo deja en el log)
"""
import logging
import os

import httpx
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("todoist")

# Datos de ejemplo usados cuando no hay token o la API falla
MOCK_STATS = {"ideas": 12, "tareas": 8, "recordatorios": 5, "total": 25}

# Etiqueta en Todoist -> clave en el JSON de respuesta
CATEGORIAS = {"idea": "ideas", "tarea": "tareas", "recordatorio": "recordatorios"}


def configurado() -> bool:
    """True si TODOIST_API_TOKEN existe y no está vacío."""
    return bool(os.getenv("TODOIST_API_TOKEN", "").strip())


def base_url() -> str:
    """URL base (configurable por si Todoist retira REST v2; ver README)."""
    return os.getenv("TODOIST_BASE_URL", "https://api.todoist.com/rest/v2").strip().rstrip("/")


def headers() -> dict:
    return {"Authorization": f"Bearer {os.getenv('TODOIST_API_TOKEN', '').strip()}"}


async def listar_tareas() -> list[dict]:
    """
    Devuelve todas las tareas activas de Todoist.
    Soporta REST v2 (lista directa) y API v1 (paginada con cursor).
    OJO: lanza httpx.HTTPError si la API falla; quien la use debe capturarlo.
    """
    tareas: list[dict] = []
    cursor = None
    async with httpx.AsyncClient(timeout=10) as client:
        while True:
            params = {"cursor": cursor} if cursor else {}
            resp = await client.get(f"{base_url()}/tasks", headers=headers(), params=params)
            resp.raise_for_status()
            data = resp.json()

            if isinstance(data, list):                    # REST v2
                tareas.extend(data)
                break
            tareas.extend(data.get("results", []))        # API v1
            cursor = data.get("next_cursor")
            if not cursor:
                break
    return tareas


async def contar_por_categoria() -> dict:
    """Cuenta tareas por etiqueta (Idea/Tarea/Recordatorio). Cae a MOCK si no hay token o falla."""
    if not configurado():
        return dict(MOCK_STATS)

    try:
        tareas = await listar_tareas()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Todoist falló (%s). Devolviendo datos mock.", exc)
        return dict(MOCK_STATS)

    conteo = {"ideas": 0, "tareas": 0, "recordatorios": 0}
    for tarea in tareas:
        etiquetas = {str(e).strip().lower() for e in tarea.get("labels", [])}
        for etiqueta, clave in CATEGORIAS.items():
            if etiqueta in etiquetas:
                conteo[clave] += 1
                break  # cada tarea cuenta una sola vez
    conteo["total"] = sum(conteo.values())
    return conteo
