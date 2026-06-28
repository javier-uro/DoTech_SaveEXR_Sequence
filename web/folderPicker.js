import { app } from "../../scripts/app.js";

// --- API helpers ------------------------------------------------------------
async function apiPost(route, body) {
    const r = await fetch(route, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body || {}),
    });
    return await r.json();
}

async function apiGet(route) {
    const r = await fetch(route);
    return await r.json();
}

// --- Bookmarks API ----------------------------------------------------------
const BM_BASE = "/dotech_saveexr_sequence/bookmarks";

async function fetchBookmarks() {
    try {
        const data = await apiGet(BM_BASE);
        return data.bookmarks || [];
    } catch {
        return [];
    }
}

async function addBookmark(path) {
    const label = path.replace(/[/\\]+$/, "").split(/[/\\]/).pop() || path;
    return await apiPost(BM_BASE + "/add", { path, label });
}

async function removeBookmark(path) {
    return await apiPost(BM_BASE + "/remove", { path });
}

// --- Modal navegador de carpetas -------------------------------------------
function openFolderBrowser(startPath) {
    return new Promise((resolve) => {
        let currentPath = startPath || "";

        const overlay = document.createElement("div");
        overlay.style.cssText =
            "position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:10000;" +
            "display:flex;align-items:center;justify-content:center;";

        const box = document.createElement("div");
        box.style.cssText =
            "background:#202020;color:#ddd;width:740px;max-height:72vh;display:flex;" +
            "flex-direction:column;border:1px solid #444;border-radius:8px;" +
            "font-family:sans-serif;font-size:13px;box-shadow:0 8px 30px rgba(0,0,0,.5);";
        overlay.appendChild(box);

        // --- Header ---------------------------------------------------------
        const title = document.createElement("div");
        title.textContent = "Elegir carpeta de salida";
        title.style.cssText =
            "padding:10px 14px;font-weight:600;border-bottom:1px solid #444;flex-shrink:0;";
        box.appendChild(title);

        // --- Path bar -------------------------------------------------------
        const pathRow = document.createElement("div");
        pathRow.style.cssText =
            "display:flex;align-items:center;padding:6px 14px;border-bottom:1px solid #333;" +
            "flex-shrink:0;gap:8px;";

        const pathBar = document.createElement("div");
        pathBar.style.cssText =
            "flex:1;color:#9cdcfe;word-break:break-all;font-family:monospace;font-size:12px;";

        const starBtn = document.createElement("button");
        starBtn.textContent = "⭐";
        starBtn.title = "Añadir carpeta actual a bookmarks";
        starBtn.style.cssText =
            "background:none;border:1px solid #555;border-radius:4px;color:#ddd;" +
            "cursor:pointer;padding:2px 7px;font-size:13px;flex-shrink:0;";
        starBtn.onclick = async () => {
            if (!currentPath) {
                pathBar.textContent = "⚠ Entra en una carpeta antes de guardar el bookmark.";
                return;
            }
            const res = await addBookmark(currentPath);
            if (res.error) {
                pathBar.textContent = "⚠ " + res.error;
                return;
            }
            renderSidebar(res.bookmarks || []);
        };

        pathRow.appendChild(pathBar);
        pathRow.appendChild(starBtn);
        box.appendChild(pathRow);

        // --- Body (sidebar + folder list) -----------------------------------
        const body = document.createElement("div");
        body.style.cssText = "display:flex;flex:1;overflow:hidden;min-height:160px;";
        box.appendChild(body);

        // Sidebar
        const sidebar = document.createElement("div");
        sidebar.style.cssText =
            "width:188px;min-width:188px;border-right:1px solid #2d2d2d;display:flex;" +
            "flex-direction:column;overflow:hidden;";

        const sidebarHeader = document.createElement("div");
        sidebarHeader.textContent = "Bookmarks";
        sidebarHeader.style.cssText =
            "padding:7px 10px;font-size:11px;font-weight:600;color:#666;" +
            "border-bottom:1px solid #2a2a2a;text-transform:uppercase;letter-spacing:.5px;flex-shrink:0;";
        sidebar.appendChild(sidebarHeader);

        const sidebarList = document.createElement("div");
        sidebarList.style.cssText = "flex:1;overflow-y:auto;";
        sidebar.appendChild(sidebarList);
        body.appendChild(sidebar);

        // Folder list
        const list = document.createElement("div");
        list.style.cssText = "flex:1;overflow-y:auto;padding:6px 0;";
        body.appendChild(list);

        // --- Footer ---------------------------------------------------------
        const footer = document.createElement("div");
        footer.style.cssText =
            "padding:10px 14px;border-top:1px solid #444;display:flex;gap:8px;" +
            "justify-content:flex-end;align-items:center;flex-shrink:0;";
        box.appendChild(footer);

        const close = (result) => {
            if (overlay.parentNode) document.body.removeChild(overlay);
            resolve(result);
        };

        // --- Sidebar rendering ----------------------------------------------
        function renderSidebar(bookmarks) {
            sidebarList.innerHTML = "";
            if (!bookmarks.length) {
                const empty = document.createElement("div");
                empty.textContent = "(sin bookmarks)";
                empty.style.cssText =
                    "padding:12px 10px;color:#555;font-style:italic;font-size:12px;";
                sidebarList.appendChild(empty);
                return;
            }
            for (const bm of bookmarks) {
                const row = document.createElement("div");
                row.style.cssText =
                    "display:flex;align-items:center;padding:6px 8px;gap:4px;";

                const label = document.createElement("div");
                label.textContent = "📁 " + bm.label;
                label.title = bm.path;
                label.style.cssText =
                    "flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" +
                    "font-size:12px;cursor:pointer;";
                label.onmouseenter = () => (label.style.color = "#9cdcfe");
                label.onmouseleave = () => (label.style.color = "");
                label.onclick = () => load(bm.path);

                const del = document.createElement("button");
                del.textContent = "🗑";
                del.title = "Eliminar bookmark";
                del.style.cssText =
                    "background:none;border:none;color:#555;cursor:pointer;" +
                    "font-size:12px;padding:0 2px;flex-shrink:0;line-height:1;";
                del.onmouseenter = () => (del.style.color = "#e06c6c");
                del.onmouseleave = () => (del.style.color = "#555");
                del.onclick = async (e) => {
                    e.stopPropagation();
                    const res = await removeBookmark(bm.path);
                    renderSidebar(res.bookmarks || []);
                };

                row.appendChild(label);
                row.appendChild(del);
                sidebarList.appendChild(row);
            }
        }

        // --- Folder browser -------------------------------------------------
        function makeRow(label, onClick, icon) {
            const row = document.createElement("div");
            row.style.cssText =
                "padding:6px 16px;cursor:pointer;display:flex;gap:8px;align-items:center;";
            row.onmouseenter = () => (row.style.background = "#2d2d2d");
            row.onmouseleave = () => (row.style.background = "");
            row.textContent = (icon || "📁") + " " + label;
            row.onclick = onClick;
            return row;
        }

        function joinPath(base, name) {
            if (!base) return name;
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

        // Footer buttons
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
            const res = await apiPost("/dotech_saveexr_sequence/mkdir", {
                path: currentPath, name,
            });
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
            "padding:6px 12px;background:#333;color:#ddd;border:1px solid #555;" +
            "border-radius:4px;cursor:pointer;";
        cancelBtn.onclick = () => close(null);
        footer.appendChild(cancelBtn);

        const okBtn = document.createElement("button");
        okBtn.textContent = "Elegir esta carpeta";
        okBtn.style.cssText =
            "padding:6px 12px;background:#2d6cdf;color:#fff;border:none;" +
            "border-radius:4px;cursor:pointer;";
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

        // Carga inicial: bookmarks + directorio de partida
        fetchBookmarks().then(renderSidebar);
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
