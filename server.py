"""Endpoints del navegador de carpetas in-app de DoTech_SaveEXR_Sequence.

Se registran en el servidor de ComfyUI (aiohttp) y los consume `web/folderPicker.js`.
Permiten listar carpetas del disco del servidor y crear carpetas nuevas, para
rellenar `output_dir` sin escribir la ruta a mano. Todo es local (localhost/LAN):
no hay red externa.
"""

import os
import string

from aiohttp import web
from server import PromptServer


def _list_drives():
    """Unidades disponibles en Windows (C:\\, D:\\, ...)."""
    drives = []
    for letter in string.ascii_uppercase:
        root = f"{letter}:\\"
        if os.path.exists(root):
            drives.append(root)
    return drives


def _is_drive_root(path):
    # "C:" o "C:\" -> raiz de unidad
    p = path.rstrip("\\/")
    return os.name == "nt" and len(p) == 2 and p[1] == ":"


@PromptServer.instance.routes.post("/dotech_saveexr_sequence/listdir")
async def listdir(request):
    try:
        data = await request.json()
    except Exception:
        data = {}
    path = (data.get("path") or "").strip()

    # Sin ruta -> raiz: en Windows mostramos las unidades; en POSIX "/".
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
                    continue  # enlaces rotos, permisos, etc.
    except PermissionError:
        return web.json_response({"error": f"Sin permiso para listar: {path}"}, status=403)
    except OSError as e:
        return web.json_response({"error": str(e)}, status=400)

    dirs.sort(key=str.lower)

    # Padre: hacia arriba; desde la raiz de una unidad se vuelve a la lista de unidades.
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
