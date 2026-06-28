"""DoTech_SaveEXR_Sequence — nodo de guardado de secuencias EXR para ComfyUI.

Escribe cada frame del batch como un .exr con numeracion controlable mediante
`start_frame`, para poder TROCEAR el workflow LTX IC-LoRA SDR->HDR sin que los
chunks se pisen (el guardado nativo siempre numera desde 0).

Reglas de correccion (no negociables):
  - NO se clampa a [0, 1] -> se conserva el rango HDR (valores scene-linear).
  - Se preservan los canales del input (3 -> RGB, 4 -> RGBA).
  - Escritura via paquete Python `OpenEXR` (>=3.2, API numpy nativa).
"""

import os
import numpy as np

try:
    import OpenEXR
    _IMPORT_ERROR = None
except Exception as e:  # ImportError u otros fallos de carga del binario
    OpenEXR = None
    _IMPORT_ERROR = e


# Etiquetas del dropdown -> constante de compresion de OpenEXR.
# Se resuelve de forma perezosa para que el modulo importe aunque OpenEXR falte.
def _compression_map():
    return {
        "zip": OpenEXR.ZIP_COMPRESSION,    # lossless, bloques de 16 scanlines (def.)
        "zips": OpenEXR.ZIPS_COMPRESSION,  # lossless, por scanline
        "piz": OpenEXR.PIZ_COMPRESSION,    # lossless, bueno con grano/ruido
        "none": OpenEXR.NO_COMPRESSION,    # sin compresion
        "dwaa": OpenEXR.DWAA_COMPRESSION,  # CON PERDIDA (no recomendado para HDR de referencia)
    }


_CHANNEL_NAMES = ["R", "G", "B", "A"]


class DoTech_SaveEXRSequence:
    """Guarda un batch de imagenes como secuencia .exr numerada."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "output_dir": ("STRING", {"default": "", "multiline": False}),
                "filename_prefix": ("STRING", {"default": "frame_"}),
                "start_frame": ("INT", {"default": 1, "min": 0, "max": 1000000000, "step": 1}),
                "padding": ("INT", {"default": 4, "min": 1, "max": 12, "step": 1}),
                "half_precision": ("BOOLEAN", {"default": True}),
                "compression": (["zip", "zips", "piz", "none", "dwaa"], {"default": "zip"}),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("images", "paths")
    FUNCTION = "save"
    OUTPUT_NODE = True
    CATEGORY = "Do_Tech/EXR"

    def save(self, images, output_dir, filename_prefix, start_frame,
             padding, half_precision, compression):
        if OpenEXR is None:
            raise RuntimeError(
                "DoTech_SaveEXR_Sequence: el paquete 'OpenEXR' (>=3.2) no esta disponible. "
                "Instalalo con:  python_embeded\\python.exe -m pip install \"OpenEXR>=3.2\"\n"
                f"Error original: {_IMPORT_ERROR}"
            )

        output_dir = (output_dir or "").strip()
        if not output_dir:
            raise ValueError(
                "DoTech_SaveEXR_Sequence: 'output_dir' esta vacio. "
                "Escribe una ruta o usa el boton 'Elegir carpeta...'."
            )
        os.makedirs(output_dir, exist_ok=True)

        # IMAGE de ComfyUI -> numpy [B, H, W, C]
        arr = images.cpu().numpy() if hasattr(images, "cpu") else np.asarray(images)
        if arr.ndim == 3:  # imagen suelta sin dimension de batch
            arr = arr[None, ...]

        np_dtype = np.float16 if half_precision else np.float32
        comp = _compression_map().get(compression, OpenEXR.ZIP_COMPRESSION)
        header = {"compression": comp, "type": OpenEXR.scanlineimage}

        written = []
        n_frames = int(arr.shape[0])
        for i in range(n_frames):
            frame = arr[i]
            if frame.ndim == 2:  # un solo canal sin eje de color
                frame = frame[..., None]
            n_channels = min(frame.shape[-1], 4)

            channels = {}
            for ch in range(n_channels):
                name = _CHANNEL_NAMES[ch]
                # NO se clampa: se escriben los valores lineales tal cual.
                channels[name] = np.ascontiguousarray(frame[..., ch].astype(np_dtype))

            filename = f"{filename_prefix}{start_frame + i:0{padding}d}.exr"
            path = os.path.join(output_dir, filename)
            with OpenEXR.File(header, channels) as outfile:
                outfile.write(path)
            written.append(path)

        msg = f"{len(written)} EXR -> {output_dir}"
        print(f"[DoTech_SaveEXR_Sequence] {msg}")
        paths_str = "\n".join(written)
        return {"ui": {"text": [msg]}, "result": (images, paths_str)}


NODE_CLASS_MAPPINGS = {"DoTech_SaveEXRSequence": DoTech_SaveEXRSequence}
NODE_DISPLAY_NAME_MAPPINGS = {"DoTech_SaveEXRSequence": "DoTech_SaveEXR_Sequence"}
