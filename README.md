# DoTech_SaveEXR_Sequence — nodo ComfyUI

**Versión 0.1** · Parte del paquete de nodos **Do_Technology** (grupo `Do_Tech` en ComfyUI).

Nodo de guardado de secuencias EXR para ComfyUI con **numeración controlable**
(`start_frame`) y un **navegador de carpetas in-app** para elegir la carpeta de
salida. Pensado para **trocear** el workflow LTX-2.3 IC-LoRA SDR→HDR sin que los
chunks se pisen.

---

## Por qué existe

Al trocear una secuencia larga (porque a 5K una sola pasada colapsa la VRAM), el
guardado nativo de EXR (`save_exr` del `LTXVHDR Decode Postprocess` y el CoCo
Saver) **siempre numera desde 0/1 en cada ejecución** → el chunk 2 pisa al chunk 1.
Este nodo deja fijar el número del primer frame, así cada chunk cae en su rango
real y **casa con la numeración del plate de origen** dentro de la misma carpeta.

---

## Características

- **`start_frame`**: número del primer frame del batch (p.ej. 1009).
- **`padding`**: dígitos del contador (`1009` → `_1009`; con 6 → `_001009`).
- **Sin clamp**: escribe los valores scene-linear tal cual → **conserva el rango HDR**.
- **Canales preservados**: 3 canales → RGB, 4 → RGBA.
- **`half_precision`**: half (16-bit) por defecto, o full (32-bit) float.
- **`compression`**: `zip` (lossless, por defecto), `zips`, `piz`, `none`, `dwaa`.
- **Pass-through**: salidas `images` (la señal intacta) + `paths` (rutas escritas).
- **Botón 📁 "Elegir carpeta…"**: abre un navegador de carpetas dentro de ComfyUI
  (portable, funciona en local y en remoto) que rellena `output_dir`. El campo de
  texto sigue editable a mano.

---

## Inputs

| Input | Tipo | Def. | Notas |
|---|---|---|---|
| `images` | IMAGE | — | Conéctalo a la salida **`hdr_linear`** del `LTXVHDR Decode Postprocess` (NO a `tonemapped`). |
| `output_dir` | STRING | — | Carpeta de salida. Se crea si no existe. Usa el botón 📁 o escríbela. |
| `filename_prefix` | STRING | `frame_` | Incluye el separador final: `shot010_v01_` → `shot010_v01_1009.exr`. |
| `start_frame` | INT | 1 | Número del primer frame del chunk. |
| `padding` | INT | 4 | Dígitos del contador. |
| `half_precision` | BOOL | true | half 16-bit / full 32-bit float. |
| `compression` | combo | `zip` | Compresión EXR. |

Patrón de salida: `{filename_prefix}{start_frame + i:0{padding}d}.exr`.

---

## Instalación

1. Copia la carpeta `DoTech_SaveEXR_Sequence/` a `ComfyUI/custom_nodes/`.
   - En `mur-77`: `D:\software_comfyui\ComfyUI_topaz_urosas\ComfyUI\custom_nodes\`
2. Instala la dependencia (en el Python de ComfyUI):
   ```powershell
   .\python_embeded\python.exe -m pip install -r ComfyUI\custom_nodes\DoTech_SaveEXR_Sequence\requirements.txt
   ```
   En `mur-77` ya está `OpenEXR 3.4.12` (API numpy OK), así que esto no cambia nada.
3. Reinicia ComfyUI. El nodo aparece como **`DoTech_SaveEXR_Sequence`** en el grupo
   **`Do_Tech ▸ EXR`** (clic derecho en el canvas → Add Node → Do_Tech → EXR).

> Requiere el paquete Python **`OpenEXR >= 3.2`** (API numpy nativa). Si falta, el
> nodo lo avisa con el comando exacto de instalación.

---

## Conexión en el workflow

En el `LTXVHDR Decode Postprocess`: apaga `save_exr` → toma la salida **`hdr_linear`**
→ `DoTech_SaveEXR_Sequence`. Al trocear, pon `start_frame` = frame real del chunk; todo
cae en la misma carpeta sin pisarse.

---

## Test rápido recomendado

Dos chunks pequeños en la **misma** carpeta:

1. `start_frame = 1`, 9 frames → `frame_0001.exr` … `frame_0009.exr`
2. `start_frame = 10`, 9 frames → `frame_0010.exr` … `frame_0018.exr`

Verifica: numeración correlativa sin pisarse, y al abrir un EXR en Nuke/renderer
los valores **superan 1.0** (rango HDR conservado).

---

## Notas

- **Tope de half float = 65504.** Si un highlight HDR lo supera, en `half` se va a
  `inf` (comportamiento estándar EXR). Por eso `half_precision = false` da el escape
  a 32-bit. **Nunca** se clampa para "arreglarlo".
- El navegador de carpetas expone el listado del filesystem del servidor por su API
  local (localhost/LAN, mismo modelo de confianza que ya tiene ComfyUI).

## Dependencias y licencia

- **Licencia del nodo:** MIT — © 2026 **Do_Technology** (titular y administrador).
  Ver `LICENSE`.
- **OpenEXR** (paquete Python) — BSD-3-Clause. Se declara como dependencia; no se
  redistribuye dentro del paquete.

---

## Changelog

### 0.1 (2026-06-28)
- Primera versión: nodo `DoTech_SaveEXR_Sequence` (OpenEXR numpy API, sin clamp, canales
  preservados, compresión configurable, pass-through) + navegador de carpetas in-app.
- Grupo ComfyUI `Do_Tech/EXR` (paraguas Do_Technology). Licencia MIT © Do_Technology.
