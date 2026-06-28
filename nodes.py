"""DoTech_SaveEXR_Sequence — nodo de guardado multi-formato para ComfyUI.

Formatos: EXR (HDR, sin clamp), PNG (8-bit), TIF (16-bit), JPG (8-bit), HDR (Radiance).
Seleccion de canales R/G/B/A independiente. Input de alpha externo. Output de alpha separado.
"""

import os
import numpy as np

# --- Dependencias opcionales -----------------------------------------------

try:
    import OpenEXR
    _EXR_ERR = None
except Exception as e:
    OpenEXR = None
    _EXR_ERR = e

try:
    from PIL import Image as _PIL
    _PIL_ERR = None
except Exception as e:
    _PIL = None
    _PIL_ERR = e

try:
    import imageio as _imageio
    _IMAGEIO_ERR = None
except Exception as e:
    _imageio = None
    _IMAGEIO_ERR = e


def _comp_map():
    return {
        "zip":  OpenEXR.ZIP_COMPRESSION,
        "zips": OpenEXR.ZIPS_COMPRESSION,
        "piz":  OpenEXR.PIZ_COMPRESSION,
        "none": OpenEXR.NO_COMPRESSION,
        "dwaa": OpenEXR.DWAA_COMPRESSION,
    }


_CH_NAMES = ["R", "G", "B", "A"]
_FORMATS  = ["exr", "png", "tif", "jpg", "hdr"]
_EXT_MAP  = {"jpg": "jpg", "jpeg": "jpg", "tif": "tif", "tiff": "tif",
             "png": "png", "hdr": "hdr", "exr": "exr"}
_PIL_MODES = {1: "L", 2: "LA", 3: "RGB", 4: "RGBA"}


# --- Escritura por formato --------------------------------------------------

def _write_exr(path, frame, selected, half_precision, compression):
    if OpenEXR is None:
        raise RuntimeError(
            f"DoTech_SaveEXR_Sequence: paquete 'OpenEXR' no disponible.\n"
            f"Instalar: python_embeded\\python.exe -m pip install \"OpenEXR>=3.2\"\n"
            f"Error: {_EXR_ERR}"
        )
    dtype = np.float16 if half_precision else np.float32
    comp  = _comp_map().get(compression, OpenEXR.ZIP_COMPRESSION)
    channels = {name: np.ascontiguousarray(frame[..., idx].astype(dtype))
                for idx, name in selected}
    with OpenEXR.File({"compression": comp, "type": OpenEXR.scanlineimage}, channels) as f:
        f.write(path)


def _sel_data(frame, selected):
    """Extrae canales seleccionados → [H, W, N]."""
    return frame[..., [idx for idx, _ in selected]]


def _u8(data):
    return (np.clip(data, 0.0, 1.0) * 255).astype(np.uint8)


def _u16(data):
    return (np.clip(data, 0.0, 1.0) * 65535).astype(np.uint16)


def _write_png(path, frame, selected):
    if _PIL is None:
        raise RuntimeError(f"DoTech_SaveEXR_Sequence (PNG): Pillow no disponible. {_PIL_ERR}")
    data = _u8(_sel_data(frame, selected))
    n    = data.shape[-1]
    img  = _PIL.fromarray(data[..., 0] if n == 1 else data, _PIL_MODES.get(n, "RGB"))
    img.save(path, format="PNG")


def _write_jpg(path, frame, selected, quality):
    if _PIL is None:
        raise RuntimeError(f"DoTech_SaveEXR_Sequence (JPG): Pillow no disponible. {_PIL_ERR}")
    # JPG no admite alpha — filtrar solo RGB
    rgb_sel = [(idx, name) for idx, name in selected if name in ("R", "G", "B")]
    if not rgb_sel:
        raise ValueError("DoTech_SaveEXR_Sequence (JPG): selecciona al menos un canal RGB.")
    data = _u8(_sel_data(frame, rgb_sel))
    # Asegurar 3 canales para JPEG
    if data.shape[-1] == 1:
        data = np.repeat(data, 3, axis=-1)
    elif data.shape[-1] == 2:
        data = np.concatenate([data, np.zeros((*data.shape[:2], 1), dtype=np.uint8)], axis=-1)
    _PIL.fromarray(data, "RGB").save(path, format="JPEG", quality=quality, subsampling=0)


def _imageio_write(path, data):
    """Escribe con imageio, compatible con v2 y v3."""
    try:
        _imageio.v3.imwrite(path, data)
    except AttributeError:
        _imageio.imwrite(path, data)


def _write_tif(path, frame, selected):
    """TIF 16-bit via imageio (preferido) o PIL 8-bit (fallback)."""
    data = _sel_data(frame, selected)
    if _imageio is not None:
        out = _u16(data)
        if out.shape[-1] == 1:
            out = out[..., 0]
        _imageio_write(path, out)
        return
    # Fallback PIL 8-bit
    if _PIL is None:
        raise RuntimeError("DoTech_SaveEXR_Sequence (TIF): ni imageio ni Pillow disponibles.")
    out = _u8(data)
    n   = out.shape[-1]
    _PIL.fromarray(out[..., 0] if n == 1 else out, _PIL_MODES.get(n, "RGB")).save(path, format="TIFF")


def _write_hdr(path, frame, selected):
    """Radiance HDR: solo canales RGB, float32, sin clamp."""
    if _imageio is None:
        raise RuntimeError(f"DoTech_SaveEXR_Sequence (HDR): imageio no disponible. {_IMAGEIO_ERR}")
    rgb_sel = [(idx, name) for idx, name in selected if name in ("R", "G", "B")]
    if not rgb_sel:
        raise ValueError("DoTech_SaveEXR_Sequence (HDR): el formato Radiance HDR requiere canales RGB.")
    data = _sel_data(frame, rgb_sel).astype(np.float32)
    if data.shape[-1] == 1:
        data = np.repeat(data, 3, axis=-1)
    elif data.shape[-1] == 2:
        data = np.concatenate([data, np.zeros((*data.shape[:2], 1), dtype=np.float32)], axis=-1)
    _imageio_write(path, data)


# --- Nodo ------------------------------------------------------------------

class DoTech_SaveEXRSequence:

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images":          ("IMAGE",),
                "output_dir":      ("STRING",  {"default": "", "multiline": False}),
                "filename_prefix": ("STRING",  {"default": "frame_"}),
                "start_frame":     ("INT",     {"default": 1, "min": 0,   "max": 1_000_000_000, "step": 1}),
                "padding":         ("INT",     {"default": 4, "min": 1,   "max": 12,            "step": 1}),
                "format":          (_FORMATS,  {"default": "exr"}),
                # Canales — toggles R/G/B/A
                "ch_r":            ("BOOLEAN", {"default": True,  "label_on": "R on", "label_off": "R off"}),
                "ch_g":            ("BOOLEAN", {"default": True,  "label_on": "G on", "label_off": "G off"}),
                "ch_b":            ("BOOLEAN", {"default": True,  "label_on": "B on", "label_off": "B off"}),
                "ch_a":            ("BOOLEAN", {"default": False, "label_on": "A on", "label_off": "A off"}),
                # Solo EXR
                "half_precision":  ("BOOLEAN", {"default": True}),
                "compression":     (["zip", "zips", "piz", "none", "dwaa"], {"default": "zip"}),
                # Solo JPG
                "jpg_quality":     ("INT",     {"default": 95, "min": 1, "max": 100, "step": 1}),
            },
            "optional": {
                "alpha": ("IMAGE",),   # canal A externo (reemplaza o añade canal A al input)
            },
        }

    RETURN_TYPES  = ("IMAGE", "IMAGE", "STRING")
    RETURN_NAMES  = ("images", "alpha", "paths")
    FUNCTION      = "save"
    OUTPUT_NODE   = True
    CATEGORY      = "Do_Tech/EXR"

    def save(self, images, output_dir, filename_prefix, start_frame, padding,
             format, ch_r, ch_g, ch_b, ch_a, half_precision, compression, jpg_quality,
             alpha=None):

        output_dir = (output_dir or "").strip()
        if not output_dir:
            raise ValueError("DoTech_SaveEXR_Sequence: 'output_dir' esta vacio.")
        os.makedirs(output_dir, exist_ok=True)

        # Tensor → numpy [B, H, W, C]
        arr = images.cpu().numpy() if hasattr(images, "cpu") else np.asarray(images)
        if arr.ndim == 3:
            arr = arr[None, ...]

        # Mezclar alpha externo
        if alpha is not None:
            a = alpha.cpu().numpy() if hasattr(alpha, "cpu") else np.asarray(alpha)
            if a.ndim == 3:
                a = a[None, ...]
            a = a[..., :1]                                          # primer canal
            if a.shape[0] == 1 and arr.shape[0] > 1:
                a = np.repeat(a, arr.shape[0], axis=0)
            if arr.shape[-1] == 3:
                arr = np.concatenate([arr, a], axis=-1)            # RGB → RGBA
            elif arr.shape[-1] >= 4:
                arr = arr.copy(); arr[..., 3:4] = a

        n_ch = arr.shape[-1]

        # Canales seleccionados
        flags    = [ch_r, ch_g, ch_b, ch_a]
        selected = [(i, _CH_NAMES[i]) for i in range(min(n_ch, 4)) if flags[i]]
        if not selected:
            raise ValueError("DoTech_SaveEXR_Sequence: selecciona al menos un canal.")

        fmt = format.lower()
        ext = _EXT_MAP.get(fmt, fmt)

        written      = []
        alpha_frames = []

        for i in range(arr.shape[0]):
            frame    = arr[i]
            filename = f"{filename_prefix}{start_frame + i:0{padding}d}.{ext}"
            path     = os.path.join(output_dir, filename)

            if   fmt == "exr":             _write_exr(path, frame, selected, half_precision, compression)
            elif fmt == "png":             _write_png(path, frame, selected)
            elif fmt in ("tif", "tiff"):   _write_tif(path, frame, selected)
            elif fmt in ("jpg", "jpeg"):   _write_jpg(path, frame, selected, jpg_quality)
            elif fmt == "hdr":             _write_hdr(path, frame, selected)

            written.append(path)

            # Alpha output: canal A si existe, 1.0 (opaco) si no
            a_ch = frame[..., 3:4] if n_ch >= 4 else np.ones((*frame.shape[:2], 1), dtype=np.float32)
            alpha_frames.append(np.repeat(a_ch, 3, axis=-1))      # [H, W, 3] para IMAGE

        import torch
        alpha_out = torch.from_numpy(np.stack(alpha_frames, axis=0).astype(np.float32))

        msg = f"{len(written)} {ext.upper()} → {output_dir}"
        print(f"[DoTech_SaveEXR_Sequence] {msg}")
        return {"ui": {"text": [msg]}, "result": (images, alpha_out, "\n".join(written))}


NODE_CLASS_MAPPINGS        = {"DoTech_SaveEXRSequence": DoTech_SaveEXRSequence}
NODE_DISPLAY_NAME_MAPPINGS = {"DoTech_SaveEXRSequence": "DoTech_SaveEXR_Sequence"}
