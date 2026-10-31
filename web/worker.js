// Runs MarkItDown under Pyodide, off the main thread.
//
// Messages in:  { type: "convert", id, name, buffer }
// Messages out: { type: "status", text }
//               { type: "progress", value, detail }
//               { type: "ready", version }
//               { type: "result", id, title, markdown }
//               { type: "error", id?, message }

const PYODIDE_VERSION = "0.29.5";
const PYODIDE_URL = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;
// Share of the progress bar for the runtime; setup() in Python reports the rest.
const RUNTIME_SHARE = 0.25;

importScripts(`${PYODIDE_URL}pyodide.js`);

const status = (text) => postMessage({ type: "status", text });
const progress = (value, detail) => postMessage({ type: "progress", value, detail });

// Python tracebacks are long; the last line carries the useful message.
// Drop the module path from the exception name, e.g. "markitdown._exceptions.".
const lastLine = (err) =>
  String(err && err.message ? err.message : err)
    .trim()
    .split("\n")
    .pop()
    .replace(/^(?:\w+\.)+(?=\w+:)/, "");

async function boot() {
  status("Loading Python runtime…");
  progress(0, "Downloading Python");
  const pyodide = await loadPyodide({ indexURL: PYODIDE_URL });
  await pyodide.loadPackage("micropip");

  const [bootstrap, manifest] = await Promise.all([
    fetch("markitdown_web.py").then((r) => r.text()),
    fetch("wheel.json").then((r) => r.json()),
  ]);
  pyodide.FS.writeFile("/home/pyodide/markitdown_web.py", bootstrap);

  status("Loading MarkItDown and its dependencies…");
  const web = pyodide.pyimport("markitdown_web");
  const wheelUrl = new URL(manifest.wheel, self.location.href).href;
  const version = await web.setup(wheelUrl, (fraction, label) =>
    progress(RUNTIME_SHARE + (1 - RUNTIME_SHARE) * fraction, label)
  );
  return { web, version };
}

const ready = boot();

ready.then(
  ({ version }) => postMessage({ type: "ready", version }),
  (err) => postMessage({ type: "error", message: `Failed to start: ${lastLine(err)}` })
);

self.onmessage = async ({ data }) => {
  if (data.type !== "convert") return;
  const { id, name, buffer } = data;
  try {
    const { web } = await ready;
    const proxy = web.convert(name, new Uint8Array(buffer));
    const { title, markdown } = proxy.toJs({ dict_converter: Object.fromEntries });
    proxy.destroy();
    postMessage({ type: "result", id, title, markdown });
  } catch (err) {
    postMessage({ type: "error", id, message: lastLine(err) });
  }
};
