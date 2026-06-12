const state = {
  tree: null,
  selectedPath: "",
  currentPath: "",
  currentIsFile: false,
  currentContent: "",
  dirty: false,
  saveTimer: null,
  pdfUrl: "",
  compiling: false
};

const editor = ace.edit("editor");
editor.setTheme("ace/theme/textmate");
editor.session.setMode("ace/mode/latex");
editor.setOptions({
  fontSize: "15px",
  showPrintMargin: false,
  wrap: true,
  useWorker: false,
  enableBasicAutocompletion: true,
  enableLiveAutocompletion: true
});

const el = {
  fileTree: document.getElementById("fileTree"),
  mainFile: document.getElementById("mainFile"),
  currentFile: document.getElementById("currentFile"),
  saveState: document.getElementById("saveState"),
  statusPill: document.getElementById("statusPill"),
  compileBtn: document.getElementById("compileBtn"),
  autoCompile: document.getElementById("autoCompile"),
  saveBtn: document.getElementById("saveBtn"),
  newFileBtn: document.getElementById("newFileBtn"),
  newDirBtn: document.getElementById("newDirBtn"),
  uploadBtn: document.getElementById("uploadBtn"),
  zipBtn: document.getElementById("zipBtn"),
  deleteBtn: document.getElementById("deleteBtn"),
  refreshBtn: document.getElementById("refreshBtn"),
  fileInput: document.getElementById("fileInput"),
  zipInput: document.getElementById("zipInput"),
  pdfFrame: document.getElementById("pdfFrame"),
  logView: document.getElementById("logView"),
  previewTab: document.getElementById("previewTab"),
  logTab: document.getElementById("logTab"),
  openPdfBtn: document.getElementById("openPdfBtn")
};

if (window.lucide) {
  window.lucide.createIcons();
}

function setStatus(text, tone = "") {
  el.statusPill.textContent = text;
  el.statusPill.className = `status-pill ${tone}`.trim();
}

function setSaveState(text) {
  el.saveState.textContent = text;
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, {
    headers: options.body instanceof FormData ? undefined : { "Content-Type": "application/json" },
    ...options
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(data.error || `HTTP ${response.status}`);
    error.data = data;
    throw error;
  }
  return data;
}

function fileIcon(name, type) {
  if (type === "dir") return "folder";
  if (name.toLowerCase().endsWith(".tex")) return "file-text";
  if (name.toLowerCase().endsWith(".bib")) return "book-open";
  if (/\.(png|jpg|jpeg|pdf|svg)$/i.test(name)) return "image";
  return "file";
}

function renderTreeNode(node, container) {
  const row = document.createElement("div");
  row.className = `tree-item ${node.path === state.selectedPath ? "active" : ""}`;
  row.dataset.path = node.path;
  row.dataset.type = node.type;
  row.title = node.path || "workspace";

  const icon = document.createElement("i");
  icon.setAttribute("data-lucide", fileIcon(node.name, node.type));

  const name = document.createElement("span");
  name.className = "name";
  name.textContent = node.name;

  row.append(icon, name);
  row.addEventListener("click", () => {
    state.selectedPath = node.path;
    if (node.type === "file") loadFile(node.path);
    renderTree();
  });

  container.appendChild(row);

  if (node.children && node.children.length) {
    const children = document.createElement("div");
    children.className = "tree-children";
    for (const child of node.children) renderTreeNode(child, children);
    container.appendChild(children);
  }
}

function renderTree() {
  el.fileTree.textContent = "";
  if (!state.tree) return;

  for (const child of state.tree.root.children) renderTreeNode(child, el.fileTree);

  if (!state.tree.root.children.length) {
    const empty = document.createElement("div");
    empty.className = "tree-item";
    empty.textContent = "workspace vacio";
    el.fileTree.appendChild(empty);
  }

  if (window.lucide) window.lucide.createIcons();
}

function renderMainFiles(texFiles) {
  const previous = el.mainFile.value;
  el.mainFile.textContent = "";

  for (const texFile of texFiles) {
    const option = document.createElement("option");
    option.value = texFile;
    option.textContent = texFile;
    el.mainFile.appendChild(option);
  }

  if (texFiles.includes(previous)) {
    el.mainFile.value = previous;
  } else if (texFiles.includes("main.tex")) {
    el.mainFile.value = "main.tex";
  } else if (texFiles[0]) {
    el.mainFile.value = texFiles[0];
  }
}

function findNode(nodes, filePath) {
  for (const node of nodes || []) {
    if (node.path === filePath) return node;
    const found = findNode(node.children, filePath);
    if (found) return found;
  }
  return null;
}

function currentPathIsFile() {
  if (!state.currentPath) return false;
  const node = findNode(state.tree?.root?.children, state.currentPath);
  if (node) return node.type === "file";
  return state.currentIsFile;
}

async function refreshTree() {
  state.tree = await requestJson("/api/tree");
  renderMainFiles(state.tree.texFiles);
  if (state.currentPath && !currentPathIsFile()) {
    state.currentPath = "";
    state.currentIsFile = false;
    state.currentContent = "";
    state.dirty = false;
    editor.session.setValue("");
    el.currentFile.textContent = "workspace";
    setSaveState("Sin cambios");
  }
  renderTree();
}

async function loadFile(filePath) {
  if (state.dirty) await saveCurrent();

  const data = await requestJson(`/api/file?path=${encodeURIComponent(filePath)}`);
  state.currentPath = data.path;
  state.selectedPath = data.path;
  state.currentIsFile = true;
  state.currentContent = data.content;
  state.dirty = false;

  editor.session.setValue(data.content);
  editor.session.setMode(data.path.toLowerCase().endsWith(".tex") ? "ace/mode/latex" : "ace/mode/text");
  el.currentFile.textContent = data.path;
  setSaveState("Sin cambios");
  renderTree();
}

async function saveCurrent() {
  if (!state.currentPath || !currentPathIsFile()) {
    state.dirty = false;
    setSaveState("Sin cambios");
    return;
  }
  const content = editor.getValue();

  setSaveState("Guardando");
  await requestJson("/api/file", {
    method: "PUT",
    body: JSON.stringify({ path: state.currentPath, content })
  });

  state.currentContent = content;
  state.dirty = false;
  setSaveState("Guardado");
  window.clearTimeout(state.saveTimer);
}

function queueSave() {
  if (!state.currentPath || !currentPathIsFile()) return;
  state.dirty = true;
  setSaveState("Editando");
  window.clearTimeout(state.saveTimer);
  state.saveTimer = window.setTimeout(() => {
    saveCurrent().catch((error) => setStatus(error.message, "error"));
  }, 700);
}

async function compile() {
  if (state.compiling) return;
  state.compiling = true;
  el.compileBtn.disabled = true;
  setStatus("Compilando", "warn");

  try {
    const selectedMain = el.mainFile.value || (state.currentPath.endsWith(".tex") ? state.currentPath : "main.tex");
    if (currentPathIsFile()) {
      await saveCurrent();
    }
    const data = await requestJson("/api/compile", {
      method: "POST",
      body: JSON.stringify({ main: selectedMain })
    });

    el.logView.textContent = data.log;
    if (data.pdfUrl) {
      state.pdfUrl = data.pdfUrl;
      el.pdfFrame.src = data.pdfUrl;
      showPreview("pdf");
    }
    setStatus(`PDF listo ${(data.durationMs / 1000).toFixed(1)}s`, "ok");
  } catch (error) {
    el.logView.textContent = error.data?.log || error.message;
    showPreview("log");
    setStatus("Error", "error");
  } finally {
    state.compiling = false;
    el.compileBtn.disabled = false;
  }
}

function showPreview(tab) {
  const showLog = tab === "log";
  el.logView.classList.toggle("hidden", !showLog);
  el.pdfFrame.classList.toggle("hidden", showLog);
  el.logTab.classList.toggle("active", showLog);
  el.previewTab.classList.toggle("active", !showLog);
}

function selectedDirectory() {
  const selectedPath = state.selectedPath || state.currentPath;
  if (!selectedPath) return "";
  const selected = document.querySelector(`.tree-item.active[data-path="${CSS.escape(selectedPath)}"]`);
  if (selected?.dataset.type === "dir") return selectedPath;
  const parts = selectedPath.split("/");
  parts.pop();
  return parts.join("/");
}

async function createEntry(kind) {
  const baseDir = selectedDirectory();
  const label = kind === "dir" ? "Nombre de carpeta" : "Nombre de archivo";
  const name = window.prompt(label, kind === "dir" ? "capitulo" : "capitulo.tex");
  if (!name) return;

  const cleanName = name.replace(/^[/\\]+/, "");
  const fullPath = baseDir ? `${baseDir}/${cleanName}` : cleanName;
  await requestJson("/api/create", {
    method: "POST",
    body: JSON.stringify({ path: fullPath, kind, content: kind === "file" ? "" : undefined })
  });

  await refreshTree();
  state.selectedPath = fullPath;
  if (kind === "file") await loadFile(fullPath);
  else renderTree();
}

async function uploadFiles(files) {
  if (!files.length) return;
  const form = new FormData();
  form.append("dir", selectedDirectory());
  for (const file of files) form.append("files", file);

  setStatus("Subiendo", "warn");
  await requestJson("/api/upload", { method: "POST", body: form });
  await refreshTree();
  setStatus("Archivos listos", "ok");
}

async function importZip(file) {
  if (!file) return;
  const form = new FormData();
  form.append("zip", file);

  setStatus("Importando ZIP", "warn");
  await requestJson("/api/import-zip", { method: "POST", body: form });
  await refreshTree();
  if (!state.currentPath && el.mainFile.value) await loadFile(el.mainFile.value);
  setStatus("ZIP importado", "ok");
}

async function deleteCurrent() {
  const targetPath = state.selectedPath || state.currentPath;
  if (!targetPath) return;
  const ok = window.confirm(`Borrar ${targetPath}?`);
  if (!ok) return;

  await requestJson(`/api/file?path=${encodeURIComponent(targetPath)}`, { method: "DELETE" });
  if (state.currentPath === targetPath || state.currentPath.startsWith(`${targetPath}/`)) {
    state.currentPath = "";
    state.currentIsFile = false;
    state.currentContent = "";
    state.dirty = false;
    editor.session.setValue("");
    el.currentFile.textContent = "workspace";
  }
  state.selectedPath = "";
  await refreshTree();
}

async function init() {
  try {
    const status = await requestJson("/api/status");
    if (status.compiler) {
      setStatus(status.compiler.kind, "ok");
    } else {
      setStatus("Sin compilador", "error");
    }

    await refreshTree();
    if (el.mainFile.value) await loadFile(el.mainFile.value);
  } catch (error) {
    setStatus(error.message, "error");
  }
}

editor.session.on("change", () => {
  if (editor.getValue() !== state.currentContent) {
    queueSave();
    if (el.autoCompile.checked) {
      window.clearTimeout(state.autoCompileTimer);
      state.autoCompileTimer = window.setTimeout(compile, 1600);
    }
  }
});

el.compileBtn.addEventListener("click", compile);
el.saveBtn.addEventListener("click", () => saveCurrent().catch((error) => setStatus(error.message, "error")));
el.refreshBtn.addEventListener("click", () => refreshTree().catch((error) => setStatus(error.message, "error")));
el.newFileBtn.addEventListener("click", () => createEntry("file").catch((error) => setStatus(error.message, "error")));
el.newDirBtn.addEventListener("click", () => createEntry("dir").catch((error) => setStatus(error.message, "error")));
el.uploadBtn.addEventListener("click", () => el.fileInput.click());
el.zipBtn.addEventListener("click", () => el.zipInput.click());
el.deleteBtn.addEventListener("click", () => deleteCurrent().catch((error) => setStatus(error.message, "error")));
el.fileInput.addEventListener("change", () => uploadFiles([...el.fileInput.files]).catch((error) => setStatus(error.message, "error")));
el.zipInput.addEventListener("change", () => importZip(el.zipInput.files[0]).catch((error) => setStatus(error.message, "error")));
el.previewTab.addEventListener("click", () => showPreview("pdf"));
el.logTab.addEventListener("click", () => showPreview("log"));
el.openPdfBtn.addEventListener("click", () => {
  if (state.pdfUrl) window.open(state.pdfUrl, "_blank", "noopener");
});

window.addEventListener("beforeunload", (event) => {
  if (!state.dirty) return;
  event.preventDefault();
  event.returnValue = "";
});

init();
