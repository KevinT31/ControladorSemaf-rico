const fs = require("node:fs");
const fsp = require("node:fs/promises");
const path = require("node:path");
const net = require("node:net");
const { spawn, spawnSync } = require("node:child_process");

const AdmZip = require("adm-zip");
const express = require("express");
const multer = require("multer");

const ROOT = __dirname;
const WORKSPACE = path.resolve(ROOT, "workspace");
const PUBLIC_DIR = path.join(ROOT, "public");
const UPLOAD_TMP = path.join(ROOT, ".uploads");
const BUILD_DIR = path.join(WORKSPACE, ".build");
const HOST = process.env.HOST || "127.0.0.1";
const PORT = Number(process.env.PORT || 3042);
const MAX_LOG_BYTES = Number(process.env.MAX_LOG_BYTES || 6 * 1024 * 1024);

const app = express();
const upload = multer({
  dest: UPLOAD_TMP,
  limits: {
    fileSize: Number(process.env.MAX_UPLOAD_BYTES || 10 * 1024 * 1024 * 1024)
  }
});

let activeCompile = null;

app.use(express.json({ limit: process.env.JSON_BODY_LIMIT || "250mb" }));

app.use("/ace", express.static(path.join(ROOT, "node_modules", "ace-builds", "src-min-noconflict")));
app.use("/lucide", express.static(path.join(ROOT, "node_modules", "lucide", "dist", "umd")));
app.use(express.static(PUBLIC_DIR, {
  setHeaders(res, filePath) {
    if (filePath.endsWith("index.html") || filePath.endsWith("app.js")) {
      res.setHeader("Cache-Control", "no-store");
    }
  }
}));

function httpError(status, message) {
  const err = new Error(message);
  err.status = status;
  return err;
}

function asyncRoute(handler) {
  return (req, res, next) => {
    Promise.resolve(handler(req, res, next)).catch(next);
  };
}

function isSubPath(parent, child) {
  const relative = path.relative(parent, child);
  return relative === "" || (!relative.startsWith("..") && !path.isAbsolute(relative));
}

function normalizeWorkspacePath(value = "") {
  const cleaned = String(value).replace(/^[/\\]+/, "");
  const fullPath = path.resolve(WORKSPACE, cleaned);

  if (!isSubPath(WORKSPACE, fullPath)) {
    throw httpError(400, "Ruta fuera del workspace.");
  }

  const parts = path.relative(WORKSPACE, fullPath).split(path.sep).filter(Boolean);
  if (parts.includes(".build")) {
    throw httpError(400, "La carpeta .build esta reservada para la compilacion.");
  }

  return fullPath;
}

function safeRelative(fullPath) {
  return path.relative(WORKSPACE, fullPath).replace(/\\/g, "/");
}

async function ensureBaseFolders() {
  await fsp.mkdir(WORKSPACE, { recursive: true });
  await fsp.mkdir(UPLOAD_TMP, { recursive: true });
}

async function exists(fullPath) {
  try {
    await fsp.access(fullPath);
    return true;
  } catch {
    return false;
  }
}

async function removeTempFile(file) {
  if (!file || !file.path) return;
  try {
    await fsp.unlink(file.path);
  } catch {
    // The temp file may already have been moved.
  }
}

async function readTree(dir, rel = "") {
  const entries = await fsp.readdir(dir, { withFileTypes: true });
  const visibleEntries = entries
    .filter((entry) => entry.name !== ".build")
    .sort((a, b) => {
      if (a.isDirectory() !== b.isDirectory()) return a.isDirectory() ? -1 : 1;
      return a.name.localeCompare(b.name, undefined, { sensitivity: "base" });
    });

  const children = [];
  for (const entry of visibleEntries) {
    const fullPath = path.join(dir, entry.name);
    const childRel = rel ? `${rel}/${entry.name}` : entry.name;

    if (entry.isDirectory()) {
      children.push({
        type: "dir",
        name: entry.name,
        path: childRel,
        children: await readTree(fullPath, childRel)
      });
      continue;
    }

    const stat = await fsp.stat(fullPath);
    children.push({
      type: "file",
      name: entry.name,
      path: childRel,
      size: stat.size,
      modified: stat.mtimeMs
    });
  }

  return children;
}

function collectTexFiles(nodes, files = []) {
  for (const node of nodes) {
    if (node.type === "file" && node.name.toLowerCase().endsWith(".tex")) {
      files.push(node.path);
    }
    if (node.children) collectTexFiles(node.children, files);
  }
  return files;
}

function localTectonicPath() {
  const exe = process.platform === "win32" ? "tectonic.exe" : "tectonic";
  return path.join(ROOT, "tools", "tectonic", exe);
}

function executableExists(command) {
  if (command.includes(path.sep) || command.includes("/") || command.includes("\\")) {
    return fs.existsSync(command);
  }

  const finder = process.platform === "win32" ? "where.exe" : "which";
  const result = spawnSync(finder, [command], { encoding: "utf8", windowsHide: true });
  return result.status === 0;
}

function findCompiler() {
  const envCompiler = process.env.LATEX_COMPILER;
  if (envCompiler && executableExists(envCompiler)) {
    return {
      kind: path.basename(envCompiler).toLowerCase().replace(/\.exe$/, ""),
      command: envCompiler,
      source: "LATEX_COMPILER"
    };
  }

  const bundledTectonic = localTectonicPath();
  if (fs.existsSync(bundledTectonic)) {
    return { kind: "tectonic", command: bundledTectonic, source: "tools/tectonic" };
  }

  for (const candidate of ["tectonic", "latexmk", "lualatex", "xelatex", "pdflatex"]) {
    if (executableExists(candidate)) {
      return { kind: candidate, command: candidate, source: "PATH" };
    }
  }

  return null;
}

function commandVersion(command) {
  const result = spawnSync(command, ["--version"], {
    encoding: "utf8",
    windowsHide: true,
    timeout: 5000
  });

  if (result.status !== 0) return null;
  return String(result.stdout || result.stderr || "").split(/\r?\n/).find(Boolean) || null;
}

function runProcess(command, args, cwd) {
  return new Promise((resolve) => {
    const startedAt = Date.now();
    let log = "";
    let bytes = 0;
    let truncated = false;

    const child = spawn(command, args, {
      cwd,
      shell: false,
      windowsHide: true,
      env: { ...process.env, max_print_line: "10000" }
    });

    function append(chunk) {
      const text = chunk.toString("utf8");
      const size = Buffer.byteLength(text);

      if (bytes < MAX_LOG_BYTES) {
        const remaining = MAX_LOG_BYTES - bytes;
        log += size > remaining ? Buffer.from(text).subarray(0, remaining).toString("utf8") : text;
      } else {
        truncated = true;
      }

      bytes += size;
      if (bytes > MAX_LOG_BYTES) truncated = true;
    }

    child.stdout.on("data", append);
    child.stderr.on("data", append);

    child.on("error", (error) => {
      resolve({
        code: -1,
        log: `${log}\n${error.message}`,
        durationMs: Date.now() - startedAt,
        args
      });
    });

    child.on("close", (code) => {
      if (truncated) {
        log += "\n\n[Log recortado en la vista web. El archivo .log completo queda en workspace/.build si el motor lo genero.]\n";
      }

      resolve({
        code,
        log,
        durationMs: Date.now() - startedAt,
        args
      });
    });
  });
}

async function runLatexCommand(compiler, mainPath) {
  const mainDir = path.dirname(mainPath);
  const mainFile = path.basename(mainPath);
  const pdfName = `${path.basename(mainFile, path.extname(mainFile))}.pdf`;
  const buildRel = path.relative(mainDir, BUILD_DIR).replace(/\\/g, "/") || ".";

  if (compiler.kind.includes("tectonic")) {
    return {
      pdfName,
      runs: [
        await runProcess(compiler.command, [
          "--keep-logs",
          "--keep-intermediates",
          "--synctex",
          "--outdir",
          buildRel,
          mainFile
        ], mainDir)
      ]
    };
  }

  if (compiler.kind.includes("latexmk")) {
    return {
      pdfName,
      runs: [
        await runProcess(compiler.command, [
          "-pdf",
          "-interaction=nonstopmode",
          "-halt-on-error",
          "-file-line-error",
          `-outdir=${buildRel}`,
          mainFile
        ], mainDir)
      ]
    };
  }

  const args = [
    "-interaction=nonstopmode",
    "-halt-on-error",
    "-file-line-error",
    `-output-directory=${buildRel}`,
    mainFile
  ];

  const firstRun = await runProcess(compiler.command, args, mainDir);
  if (firstRun.code !== 0) {
    return { pdfName, runs: [firstRun] };
  }

  const secondRun = await runProcess(compiler.command, args, mainDir);
  return { pdfName, runs: [firstRun, secondRun] };
}

async function prepareBuildDir() {
  const resolvedBuild = path.resolve(BUILD_DIR);
  if (!isSubPath(WORKSPACE, resolvedBuild) || path.basename(resolvedBuild) !== ".build") {
    throw httpError(500, "Carpeta build invalida.");
  }

  await fsp.rm(resolvedBuild, { recursive: true, force: true });
  await fsp.mkdir(resolvedBuild, { recursive: true });
}

app.get("/api/status", asyncRoute(async (_req, res) => {
  await ensureBaseFolders();
  const compiler = findCompiler();
  res.json({
    workspace: WORKSPACE,
    compiler: compiler
      ? { ...compiler, version: commandVersion(compiler.command) }
      : null
  });
}));

app.get("/api/tree", asyncRoute(async (_req, res) => {
  await ensureBaseFolders();
  const children = await readTree(WORKSPACE);
  res.json({
    root: { type: "dir", name: "workspace", path: "", children },
    texFiles: collectTexFiles(children)
  });
}));

app.get("/api/file", asyncRoute(async (req, res) => {
  const fullPath = normalizeWorkspacePath(req.query.path || "");
  const stat = await fsp.stat(fullPath);
  if (!stat.isFile()) throw httpError(400, "La ruta no es un archivo.");

  res.json({
    path: safeRelative(fullPath),
    content: await fsp.readFile(fullPath, "utf8"),
    size: stat.size,
    modified: stat.mtimeMs
  });
}));

app.put("/api/file", asyncRoute(async (req, res) => {
  if (!String(req.body.path || "").trim()) {
    throw httpError(400, "Selecciona un archivo para guardar.");
  }

  const fullPath = normalizeWorkspacePath(req.body.path || "");
  const content = typeof req.body.content === "string" ? req.body.content : "";
  if (await exists(fullPath)) {
    const stat = await fsp.stat(fullPath);
    if (stat.isDirectory()) {
      throw httpError(400, "La ruta seleccionada es una carpeta, no un archivo.");
    }
  }

  await fsp.mkdir(path.dirname(fullPath), { recursive: true });
  await fsp.writeFile(fullPath, content, "utf8");
  const stat = await fsp.stat(fullPath);

  res.json({
    ok: true,
    path: safeRelative(fullPath),
    size: stat.size,
    modified: stat.mtimeMs
  });
}));

app.post("/api/create", asyncRoute(async (req, res) => {
  const kind = req.body.kind === "dir" ? "dir" : "file";
  const fullPath = normalizeWorkspacePath(req.body.path || "");
  if (await exists(fullPath)) throw httpError(409, "Ya existe un archivo o carpeta con esa ruta.");

  if (kind === "dir") {
    await fsp.mkdir(fullPath, { recursive: true });
  } else {
    await fsp.mkdir(path.dirname(fullPath), { recursive: true });
    await fsp.writeFile(fullPath, req.body.content || "", "utf8");
  }

  res.json({ ok: true, path: safeRelative(fullPath), kind });
}));

app.delete("/api/file", asyncRoute(async (req, res) => {
  const rel = String(req.query.path || "");
  if (!rel.trim()) throw httpError(400, "No se puede borrar el workspace completo.");

  const fullPath = normalizeWorkspacePath(rel);
  await fsp.rm(fullPath, { recursive: true, force: true });
  res.json({ ok: true });
}));

app.post("/api/upload", upload.array("files"), asyncRoute(async (req, res) => {
  const targetDir = normalizeWorkspacePath(req.body.dir || "");
  const saved = [];

  try {
    await fsp.mkdir(targetDir, { recursive: true });

    for (const file of req.files || []) {
      const name = path.basename(file.originalname || file.filename);
      const destination = normalizeWorkspacePath(path.join(safeRelative(targetDir), name));
      await fsp.rename(file.path, destination);
      saved.push(safeRelative(destination));
    }
  } finally {
    await Promise.all((req.files || []).map(removeTempFile));
  }

  res.json({ ok: true, saved });
}));

app.post("/api/import-zip", upload.single("zip"), asyncRoute(async (req, res) => {
  if (!req.file) throw httpError(400, "No se recibio un ZIP.");

  let written = 0;
  try {
    const zip = new AdmZip(req.file.path);
    for (const entry of zip.getEntries()) {
      const entryName = entry.entryName.replace(/^[/\\]+/, "");
      if (!entryName) continue;

      const fullPath = normalizeWorkspacePath(entryName);
      if (entry.isDirectory) {
        await fsp.mkdir(fullPath, { recursive: true });
        continue;
      }

      await fsp.mkdir(path.dirname(fullPath), { recursive: true });
      await fsp.writeFile(fullPath, entry.getData());
      written += 1;
    }
  } finally {
    await removeTempFile(req.file);
  }

  res.json({ ok: true, written });
}));

app.post("/api/compile", asyncRoute(async (req, res) => {
  if (activeCompile) {
    throw httpError(409, "Ya hay una compilacion en curso.");
  }

  const mainPath = normalizeWorkspacePath(req.body.main || "main.tex");
  if (!(await exists(mainPath))) {
    throw httpError(404, "No existe el archivo principal seleccionado.");
  }

  const mainStat = await fsp.stat(mainPath);
  if (!mainStat.isFile()) {
    throw httpError(400, "El archivo principal debe ser un .tex, no una carpeta.");
  }

  if (!mainPath.toLowerCase().endsWith(".tex")) {
    throw httpError(400, "El archivo principal debe tener extension .tex.");
  }

  const compiler = findCompiler();
  if (!compiler) {
    throw httpError(503, "No se encontro compilador LaTeX. Ejecuta npm run install-tectonic o instala MiKTeX/TeX Live.");
  }

  activeCompile = { startedAt: Date.now(), main: safeRelative(mainPath) };

  try {
    await prepareBuildDir();
    const result = await runLatexCommand(compiler, mainPath);
    const combinedLog = result.runs
      .map((run, index) => `$ ${path.basename(compiler.command)} ${run.args.join(" ")}\n${run.log}`.trimEnd())
      .join("\n\n");

    const failedRun = result.runs.find((run) => run.code !== 0);
    const pdfPath = path.join(BUILD_DIR, result.pdfName);
    const pdfExists = await exists(pdfPath);
    const ok = !failedRun && pdfExists;

    if (ok) {
      await fsp.copyFile(pdfPath, path.join(BUILD_DIR, "latest.pdf"));
    }

    res.status(ok ? 200 : 422).json({
      ok,
      compiler,
      pdfName: result.pdfName,
      pdfUrl: ok ? `/api/pdf?t=${Date.now()}` : null,
      durationMs: result.runs.reduce((total, run) => total + run.durationMs, 0),
      log: combinedLog || "(sin salida del compilador)"
    });
  } finally {
    activeCompile = null;
  }
}));

app.get("/api/pdf", asyncRoute(async (_req, res) => {
  const pdfPath = path.join(BUILD_DIR, "latest.pdf");
  if (!(await exists(pdfPath))) throw httpError(404, "Todavia no hay PDF compilado.");
  res.sendFile(pdfPath, { dotfiles: "allow" });
}));

app.use((err, _req, res, _next) => {
  const status = err.status || 500;
  if (status >= 500) console.error(err);
  res.status(status).json({ error: err.message || "Error interno." });
});

function canListen(port) {
  return new Promise((resolve) => {
    const tester = net.createServer()
      .once("error", () => resolve(false))
      .once("listening", () => tester.once("close", () => resolve(true)).close())
      .listen(port, HOST);
  });
}

async function pickPort(startPort) {
  for (let port = startPort; port < startPort + 30; port += 1) {
    if (await canListen(port)) return port;
  }
  return 0;
}

async function start() {
  await ensureBaseFolders();
  const port = await pickPort(PORT);
  app.listen(port, HOST, () => {
    console.log(`OverLeaf Local listo en http://${HOST}:${port}`);
    console.log(`Workspace: ${WORKSPACE}`);
  });
}

start().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
