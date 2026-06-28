import { app } from "../../scripts/app.js";

// --- API helper -------------------------------------------------------------
async function apiPost(route, body) {
    const r = await fetch(route, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body || {}),
    });
    return await r.json();
}

// --- Modal navegador de carpetas -------------------------------------------
// Devuelve una promesa que resuelve con la ruta elegida (o null si se cancela).
function openFolderBrowser(startPath) {
    return new Promise((resolve) => {
        let currentPath = startPath || "";

        const overlay = document.createElement("div");
        overlay.style.cssText =
            "position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:10000;" +
            "display:flex;align-items:center;justify-content:center;";

        const box = document.createElement("div");
        box.style.cssText =
            "background:#202020;color:#ddd;width:560px;max-height:72vh;display:flex;" +
            "flex-direction:column;border:1px solid #444;border-radius:8px;" +
            "font-family:sans-serif;font-size:13px;box-shadow:0 8px 30px rgba(0,0,0,.5);";
        overlay.appendChild(box);

        const title = document.createElement("div");
        title.textContent = "Elegir carpeta de salida";
        title.style.cssText = "padding:10px 14px;font-weight:600;border-bottom:1px solid #444;";
        box.appendChild(title);

        const pathBar = document.createElement("div");
        pathBar.style.cssText =
            "padding:8px 14px;border-bottom:1px solid #333;color:#9cdcfe;" +
            "word-break:break-all;font-family:monospace;";
        box.appendChild(pathBar);

        const list = document.createElement("div");
        list.style.cssText = "flex:1;overflow-y:auto;padding:6px 0;min-height:160px;";
        box.appendChild(list);

        const footer = document.createElement("div");
        footer.style.cssText =
            "padding:10px 14px;border-top:1px solid #444;display:flex;gap:8px;" +
            "justify-content:flex-end;align-items:center;";
        box.appendChild(footer);

        const close = (result) => {
            if (overlay.parentNode) document.body.removeChild(overlay);
            resolve(result);
        };

        function makeRow(label, onClick, icon) {
            const row = document.createElement("div");
            row.style.cssText = "padding:6px 16px;cursor:pointer;display:flex;gap:8px;align-items:center;";
            row.onmouseenter = () => (row.style.background = "#2d2d2d");
            row.onmouseleave = () => (row.style.background = "");
            row.textContent = (icon || "📁") + " " + label;
            row.onclick = onClick;
            return row;
        }

        function joinPath(base, name) {
            if (!base) return name; // raiz -> el nombre ya es la unidad "C:\\"
            const sep = base.endsWith("\\") || base.endsWith("/") ? "" : "\\";
            return base + sep + name;
        }

        async function load(path) {
            const data = await apiPost("/dotech_saveexr_sequence/listdir", { path });
            if (data.error) {
                pathBar.textContent = "⚠ " + data.error;
                return;
            }
            currentPath = data.path || "";
            pathBar.textContent = currentPath || "(unidades)";
            list.innerHTML = "";

            if (data.parent !== null && data.parent !== undefined) {
                list.appendChild(makeRow(".. (subir)", () => load(data.parent), "⬆"));
            }
            for (const d of data.dirs) {
                const target = data.is_root ? d : joinPath(currentPath, d);
                list.appendChild(makeRow(d, () => load(target)));
            }
            if (data.dirs.length === 0) {
                const empty = document.createElement("div");
                empty.textContent = "(sin subcarpetas)";
                empty.style.cssText = "padding:6px 16px;color:#777;font-style:italic;";
                list.appendChild(empty);
            }
        }

        const newBtn = document.createElement("button");
        newBtn.textContent = "Nueva carpeta";
        newBtn.style.cssText =
            "margin-right:auto;padding:6px 10px;background:#333;color:#ddd;" +
            "border:1px solid #555;border-radius:4px;cursor:pointer;";
        newBtn.onclick = async () => {
            if (!currentPath) {
                pathBar.textContent = "⚠ Entra en una carpeta antes de crear una nueva.";
                return;
            }
            const name = prompt("Nombre de la nueva carpeta:");
            if (!name) return;
            const res = await apiPost("/dotech_saveexr_sequence/mkdir", { path: currentPath, name });
            if (res.error) {
                pathBar.textContent = "⚠ " + res.error;
                return;
            }
            load(res.path);
        };
        footer.appendChild(newBtn);

        const cancelBtn = document.createElement("button");
        cancelBtn.textContent = "Cancelar";
        cancelBtn.style.cssText =
            "padding:6px 12px;background:#333;color:#ddd;border:1px solid #555;border-radius:4px;cursor:pointer;";
        cancelBtn.onclick = () => close(null);
        footer.appendChild(cancelBtn);

        const okBtn = document.createElement("button");
        okBtn.textContent = "Elegir esta carpeta";
        okBtn.style.cssText =
            "padding:6px 12px;background:#2d6cdf;color:#fff;border:none;border-radius:4px;cursor:pointer;";
        okBtn.onclick = () => {
            if (!currentPath) {
                pathBar.textContent = "⚠ Entra en una carpeta primero.";
                return;
            }
            close(currentPath);
        };
        footer.appendChild(okBtn);

        overlay.onclick = (e) => {
            if (e.target === overlay) close(null);
        };

        document.body.appendChild(overlay);
        load(currentPath);
    });
}

// --- Registro de la extension ----------------------------------------------
app.registerExtension({
    name: "DoTech_SaveEXRSequence.FolderPicker",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "DoTech_SaveEXRSequence") return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const ret = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;
            const self = this;
            this.addWidget("button", "📁 Elegir carpeta…", "browse", async () => {
                const w = self.widgets.find((x) => x.name === "output_dir");
                const start = w && w.value ? w.value : "";
                const chosen = await openFolderBrowser(start);
                if (chosen && w) {
                    w.value = chosen;
                    self.setDirtyCanvas(true, true);
                }
            });
            return ret;
        };
    },
});
