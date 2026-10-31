"use strict";

const worker = new Worker("worker.js");
const statusEl = document.getElementById("status");
const versionEl = document.getElementById("version");
const progressEl = document.getElementById("progress");
const progressBar = document.getElementById("progress-bar");
const progressFill = document.getElementById("progress-fill");
const progressDetail = document.getElementById("progress-detail");
const drop = document.getElementById("drop");
const fileInput = document.getElementById("file");
const results = document.getElementById("results");

const pending = new Map(); // conversion id -> card
let nextId = 0;

function setStatus(text, state) {
  statusEl.textContent = text;
  statusEl.className = state || "";
  progressEl.classList.toggle("idle", Boolean(state));
}

function setProgress(value, detail) {
  const percent = Math.round(value * 100);
  progressFill.style.width = `${percent}%`;
  progressBar.setAttribute("aria-valuenow", percent);
  progressBar.setAttribute("aria-valuetext", detail);
  progressDetail.textContent = detail;
}

function el(tag, props = {}, children = []) {
  const node = Object.assign(document.createElement(tag), props);
  node.append(...children);
  return node;
}

function markdownName(name) {
  return name.replace(/\.[^./\\]+$/, "") + ".md";
}

function download(name, text) {
  const url = URL.createObjectURL(new Blob([text], { type: "text/markdown;charset=utf-8" }));
  const a = el("a", { href: url, download: name });
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// navigator.clipboard only exists on HTTPS, and the site is also served over HTTP.
async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    const area = el("textarea", { value: text });
    area.style.position = "fixed";
    document.body.append(area);
    area.select();
    const copied = document.execCommand("copy");
    area.remove();
    return copied;
  }
}

function createCard(file) {
  const meta = el("span", { className: "result-meta", textContent: "Converting…" });
  const copyBtn = el("button", { type: "button", textContent: "Copy", disabled: true });
  const saveBtn = el("button", { type: "button", className: "primary", textContent: "Download .md", disabled: true });
  const removeBtn = el("button", { type: "button", textContent: "✕", title: "Remove", ariaLabel: `Remove ${file.name}` });
  const head = el("div", { className: "result-head" }, [
    el("span", { className: "result-name", textContent: file.name }),
    meta,
    el("div", { className: "actions" }, [copyBtn, saveBtn, removeBtn]),
  ]);
  const card = el("article", { className: "result" }, [head]);
  removeBtn.addEventListener("click", () => card.remove());
  results.prepend(card);

  return {
    done(markdown) {
      meta.textContent = `${markdown.length.toLocaleString()} characters`;
      card.append(el("pre", { className: "output", textContent: markdown || "(no text content found)" }));
      copyBtn.disabled = saveBtn.disabled = !markdown;
      copyBtn.addEventListener("click", async () => {
        copyBtn.textContent = (await copyText(markdown)) ? "Copied" : "Copy failed";
        setTimeout(() => (copyBtn.textContent = "Copy"), 1500);
      });
      saveBtn.addEventListener("click", () => download(markdownName(file.name), markdown));
    },
    fail(message) {
      meta.textContent = "Failed";
      meta.classList.add("err");
      copyBtn.remove();
      saveBtn.remove();
      card.append(el("p", { className: "error-text", textContent: message }));
    },
  };
}

async function convert(files) {
  for (const file of files) {
    const id = nextId++;
    pending.set(id, createCard(file));
    const buffer = await file.arrayBuffer();
    worker.postMessage({ type: "convert", id, name: file.name, buffer }, [buffer]);
  }
}

worker.onmessage = ({ data }) => {
  switch (data.type) {
    case "status":
      setStatus(data.text);
      break;
    case "progress":
      setProgress(data.value, data.detail);
      break;
    case "ready":
      setStatus("Ready: files are converted locally", "ready");
      versionEl.textContent = `MarkItDown v${data.version}.`;
      break;
    case "result":
      pending.get(data.id)?.done(data.markdown);
      pending.delete(data.id);
      break;
    case "error":
      if (data.id === undefined) {
        setStatus(data.message, "failed");
        for (const card of pending.values()) card.fail(data.message);
        pending.clear();
      } else {
        pending.get(data.id)?.fail(data.message);
        pending.delete(data.id);
      }
      break;
  }
};

worker.onerror = (e) => setStatus(`Failed to start: ${e.message}`, "failed");

fileInput.addEventListener("change", () => {
  convert([...fileInput.files]);
  fileInput.value = "";
});

drop.addEventListener("keydown", (e) => {
  if (e.key === "Enter" || e.key === " ") {
    e.preventDefault();
    fileInput.click();
  }
});

for (const type of ["dragenter", "dragover"]) {
  drop.addEventListener(type, (e) => {
    e.preventDefault();
    drop.classList.add("over");
  });
}
for (const type of ["dragleave", "drop"]) {
  drop.addEventListener(type, () => drop.classList.remove("over"));
}
drop.addEventListener("drop", (e) => {
  e.preventDefault();
  convert([...e.dataTransfer.files]);
});

// Dropping a file outside the zone shouldn't navigate away from the page.
window.addEventListener("dragover", (e) => e.preventDefault());
window.addEventListener("drop", (e) => e.preventDefault());
