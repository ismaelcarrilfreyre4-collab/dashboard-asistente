"""
Cliente asíncrono de Notion (versión 2022-06-28) con fallback a datos MOCK.

Regla:
  - Sin NOTION_API_TOKEN o sin NOTION_DATABASE_ID -> devuelve notas MOCK
  - Con ambos                                     -> lee la base de datos real
  - Con ambos pero la API falla                   -> devuelve notas MOCK (y lo deja en el log)
"""
import logging
import os
from datetime import datetime, timedelta, timezone

import httpx
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("notion")

NOTION_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


def configurado() -> bool:
    """True si NOTION_API_TOKEN y NOTION_DATABASE_ID existen y no están vacíos."""
    return bool(os.getenv("NOTION_API_TOKEN", "").strip() and os.getenv("NOTION_DATABASE_ID", "").strip())


def headers() -> dict:
    return {
        "Authorization": f"Bearer {os.getenv('NOTION_API_TOKEN', '').strip()}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


# ------------------------------------------------------------------ MOCK
def notas_mock(limit: int = 20) -> list[dict]:
    """5 notas de ejemplo (las 3 categorías), con fechas relativas a 'ahora', más recientes primero."""
    ahora = datetime.now(timezone.utc).replace(microsecond=0)

    def f(horas: int) -> str:
        return (ahora - timedelta(hours=horas)).isoformat().replace("+00:00", "Z")

    notas = [
        {"id": "1", "titulo": "Comprar pan mañana", "resumen": "Recordatorio de comprar pan",
         "categoria": "Recordatorio", "fecha": f(1),
         "transcripcion": "Recordarme comprar pan mañana por favor"},
        {"id": "2", "titulo": "App de recetas con IA", "resumen": "Idea: app que sugiere recetas según los ingredientes de la nevera",
         "categoria": "Idea", "fecha": f(5),
         "transcripcion": "Se me ocurrió una app que te sugiera recetas con lo que tengas en la nevera usando inteligencia artificial"},
        {"id": "3", "titulo": "Enviar informe al cliente", "resumen": "Tarea: enviar el informe mensual al cliente antes del viernes",
         "categoria": "Tarea", "fecha": f(24),
         "transcripcion": "Tengo que enviar el informe mensual al cliente antes del viernes"},
        {"id": "4", "titulo": "Llamar al dentista", "resumen": "Recordatorio: pedir cita con el dentista la próxima semana",
         "categoria": "Recordatorio", "fecha": f(30),
         "transcripcion": "Recuérdame llamar al dentista la semana que viene para pedir cita"},
        {"id": "5", "titulo": "Newsletter semanal", "resumen": "Idea: lanzar una newsletter semanal con novedades del proyecto",
         "categoria": "Idea", "fecha": f(48),
         "transcripcion": "Podríamos lanzar una newsletter semanal con las novedades del proyecto"},
    ]
    return notas[:limit]


# ------------------------------------------------- Helpers de lectura
def _texto(prop: dict | None, clave: str) -> str:
    """Une el plain_text de una propiedad title / rich_text."""
    if not prop:
        return ""
    return "".join(p.get("plain_text", "") for p in prop.get(clave, []) or [])


def _titulo(props: dict) -> str:
    """Busca la propiedad de tipo 'title' sin importar su nombre (Nombre, Título...)."""
    for prop in props.values():
        if prop.get("type") == "title":
            return _texto(prop, "title")
    return ""


def _propiedad(props: dict, *nombres: str) -> dict | None:
    """Primera propiedad que exista entre varios nombres posibles."""
    for nombre in nombres:
        if nombre in props:
            return props[nombre]
    return None


def _normalizar(pagina: dict) -> dict:
    """Convierte una página de Notion al formato simple que consume el frontend."""
    props = pagina.get("properties", {})

    categoria = _propiedad(props, "Categoría", "Categoria")
    categoria = ((categoria or {}).get("select") or {}).get("name", "")

    fecha = _propiedad(props, "Fecha")
    fecha = ((fecha or {}).get("date") or {}).get("start") or pagina.get("created_time", "")

    return {
        "id": pagina.get("id", ""),
        "titulo": _titulo(props),
        "resumen": _texto(_propiedad(props, "Resumen"), "rich_text"),
        "categoria": categoria,
        "fecha": fecha,
        "transcripcion": _texto(_propiedad(props, "Transcripción", "Transcripcion"), "rich_text"),
    }


async def _consultar(client: httpx.AsyncClient, body: dict) -> dict:
    db_id = os.getenv("NOTION_DATABASE_ID", "").strip()
    resp = await client.post(f"{NOTION_BASE}/databases/{db_id}/query", headers=headers(), json=body)
    resp.raise_for_status()
    return resp.json()


# --------------------------------------------------------- Función pública
async def listar_notas(limit: int = 20) -> list[dict]:
    """Últimas `limit` notas (más recientes primero). Cae a MOCK si no hay credenciales o falla."""
    limit = max(1, min(limit, 100))  # Notion permite máx. 100 por página

    if not configurado():
        return notas_mock(limit)

    body = {"page_size": limit, "sorts": [{"property": "Fecha", "direction": "descending"}]}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                data = await _consultar(client, body)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code != 400:
                    raise
                # "Fecha" no existe o no es ordenable: ordenar por fecha de creación
                body["sorts"] = [{"timestamp": "created_time", "direction": "descending"}]
                data = await _consultar(client, body)
        return [_normalizar(p) for p in data.get("results", [])]
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Notion falló (%s). Devolviendo datos mock.", exc)
        return notas_mock(limit)
