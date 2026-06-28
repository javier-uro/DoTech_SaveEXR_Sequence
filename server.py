"""Endpoints del navegador de carpetas in-app de DoTech_SaveEXR_Sequence.

Se registran en el servidor de ComfyUI (aiohttp) y los consume `web/folderPicker.js`.
Permiten listar carpetas del disco del servidor, crear carpetas nuevas y gestionar
bookmarks de directorios de uso frecuente. Todo es local (localhost/LAN): no hay
red externa.

Bookmarks: se guardan en `data/bookmarks.json` junto al paquete (excluido del git).
"""

import json
import os
import pathlib
import string
import threading

from aiohttp import web
from server import PromptServer

_DATA_DIR = pathlib.Path(__file__).parent / "data"
_BOOKMARKS_FILE = _DATA_DIR / "bookmarks.json"
_bm_lock = threading.Lock()


def _list_drives():
    """Unidades disponibles en Windows (C:\\, D:\\, ...)."""
    drives = []
    for letter in string.ascii_uppercase:
        root = f"{letter}:\\"
        if os.path.exists(root):
            drives.append(root)
    return drives


def _is_drive_root(path):
    p = path.rstrip("\\/")
    return os.name == "nt" and len(p) == 2 and p[1] == ":"


def _load_bookmarks():
    try:
        with open(_BOOKMARKS_FILE, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return []


def _save_bookmarks(bookmarks):
    _DATA_DIR.mkdir(exist_ok=True)
    with open(_BOOKMARKS_FILE, "w", encoding="utf-8") as f:
        json.dump(bookmarks, f, ensure_ascii=False, indent=2)


# --- Navegador de carpetas --------------------------------------------------

@PromptServer.instance.routes.post("/dotech_saveexr_sequence/listdir")
async def listdir(request):
    try:
        data = await request.json()
    except Exception:
        data = {}
    path = (data.get("path") or "").strip()

    if not path:
        if os.name == "nt":
            return web.json_response({
                "path": "", "parent": None, "is_root": True,
                "dirs": _list_drives(),
            })
        path = "/"

    path = os.path.abspath(path)
    if not os.path.isdir(path):
        return web.json_response({"error": f"No es una carpeta: {path}"}, status=400)

    dirs = []
    try:
        with os.scandir(path) as it:
            for entry in it:
                try:
                    if entry.is_dir():
                        dirs.append(entry.name)
                except OSError:
                    continue
    except PermissionError:
        return web.json_response({"error": f"Sin permiso para listar: {path}"}, status=403)
    except OSError as e:
        return web.json_response({"error": str(e)}, status=400)

    dirs.sort(key=str.lower)

    if _is_drive_root(path):
        parent = ""
    else:
        parent = os.path.dirname(path.rstrip("\\/"))

    return web.json_response({
        "path": path, "parent": parent, "is_root": False, "dirs": dirs,
    })


@PromptServer.instance.routes.post("/dotech_saveexr_sequence/mkdir")
async def mkdir(request):
    try:
        data = await request.json()
    except Exception:
        data = {}
    path = (data.get("path") or "").strip()
    name = (data.get("name") or "").strip()

    if not path or not name:
        return web.json_response({"error": "Faltan 'path' o 'name'."}, status=400)
    if any(bad in name for bad in ("\\", "/", "..", ":")):
        return web.json_response({"error": "Nombre de carpeta invalido."}, status=400)

    new_path = os.path.join(path, name)
    try:
        os.makedirs(new_path, exist_ok=True)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=400)

    return web.json_response({"path": new_path})


# --- Bookmarks --------------------------------------------------------------

@PromptServer.instance.routes.get("/dotech_saveexr_sequence/bookmarks")
async def get_bookmarks(request):
    with _bm_lock:
        bm = _load_bookmarks()
    return web.json_response({"bookmarks": bm})


@PromptServer.instance.routes.post("/dotech_saveexr_sequence/bookmarks/add")
async def add_bookmark(request):
    try:
        data = await request.json()
    except Exception:
        data = {}
    path = (data.get("path") or "").strip()
    label = (data.get("label") or "").strip()
    if not label:
        label = os.path.basename(path.rstrip("\\/")) or path
    if not path:
        return web.json_response({"error": "Falta 'path'."}, status=400)
    with _bm_lock:
        bm = _load_bookmarks()
        if not any(b["path"] == path for b in bm):
            bm.append({"label": label, "path": path})
            _save_bookmarks(bm)
    return web.json_response({"bookmarks": bm})


@PromptServer.instance.routes.post("/dotech_saveexr_sequence/bookmarks/remove")
async def remove_bookmark(request):
    try:
        data = await request.json()
    except Exception:
        data = {}
    path = (data.get("path") or "").strip()
    with _bm_lock:
        bm = _load_bookmarks()
        bm = [b for b in bm if b["path"] != path]
        _save_bookmarks(bm)
    return web.json_response({"bookmarks": bm})
