"""DoTech_SaveEXR_Sequence — custom node de ComfyUI.

Guardado de secuencias EXR con numeracion controlable (start_frame) + navegador
de carpetas in-app para elegir la carpeta de salida. Pensado para trocear el
workflow LTX IC-LoRA SDR->HDR sin que los chunks se pisen.
"""

from .nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

__version__ = "0.3.0"

# Endpoints del navegador de carpetas. Se envuelve en try/except para que un
# fallo registrando rutas no impida cargar el nodo en si.
try:
    from . import server  # noqa: F401  (registra /dotech_saveexr_sequence/*)
except Exception as e:
    print(f"[DoTech_SaveEXR_Sequence] Aviso: no se pudo registrar el navegador de "
          f"carpetas ({e}). El nodo funciona igual; escribe la ruta a mano.")

# Carpeta con la extension de frontend (boton + modal).
WEB_DIRECTORY = "./web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
