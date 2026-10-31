"""
Browser bootstrap for MarkItDown running under Pyodide.

Installs the dependencies that work in WebAssembly, stubs out the two that
cannot load there (magika, pypdfium2), then installs the MarkItDown wheel
built from this repository.
"""

import importlib
import io
import os
import re
import sys
import types

import micropip

# Dependencies that install cleanly under Pyodide. Version bounds mirror
# packages/markitdown/pyproject.toml.
DEPENDENCIES = [
    "beautifulsoup4",
    "requests",
    "markdownify",
    "charset-normalizer",
    "defusedxml",
    "python-pptx",
    "mammoth>=1.12.2,<2",
    "lxml",
    "pandas",
    "openpyxl",
    "xlrd",
    "pdfminer.six>=20251230",
    "olefile",
]

# Measured cold-start seconds, used to weight the progress bar. Importing takes
# longer than installing, so an unweighted bar would stall near the end.
INSTALL_SECONDS = 0.5
IMPORT_SECONDS = {
    "requests": 1,
    "bs4": 0.5,
    "pandas": 6,
    "pdfminer.high_level": 0.5,
    "pptx": 1,
    "openpyxl": 1,
}
MARKITDOWN_IMPORT_SECONDS = 1

_md = None
StreamInfo = None


def _install_stubs() -> None:
    # magika needs onnxruntime, which has no WebAssembly build. Reporting a
    # non-"ok" status makes MarkItDown fall back to extension/mimetype guesses.
    magika = types.ModuleType("magika")

    class _NoResult:
        status = "unavailable"

    class Magika:
        def identify_stream(self, stream):
            return _NoResult()

    magika.Magika = Magika
    sys.modules["magika"] = magika

    # pdfplumber imports pypdfium2 only to render pages as images, which
    # MarkItDown never does. The real package crashes the Pyodide runtime.
    pypdfium2 = types.ModuleType("pypdfium2")

    class PdfiumError(Exception):
        pass

    def PdfDocument(*args, **kwargs):
        raise PdfiumError("PDF page rendering is not available in the browser")

    pypdfium2.PdfiumError = PdfiumError
    pypdfium2.PdfDocument = PdfDocument
    sys.modules["pypdfium2"] = pypdfium2


async def setup(wheel_url: str, on_progress) -> str:
    """Install and import everything, calling on_progress(fraction, label) per step."""
    global _md, StreamInfo

    total = (
        INSTALL_SECONDS * (len(DEPENDENCIES) + 2)
        + sum(IMPORT_SECONDS.values())
        + MARKITDOWN_IMPORT_SECONDS
    )
    elapsed = 0.0

    def step(label: str, seconds: float) -> None:
        nonlocal elapsed
        on_progress(elapsed / total, label)
        elapsed += seconds

    # One at a time, because micropip reports nothing during a combined install.
    for requirement in DEPENDENCIES:
        step(f"Installing {re.split(r'[<>=!~]', requirement)[0]}", INSTALL_SECONDS)
        await micropip.install(requirement)

    # Skip pdfplumber's pypdfium2 dependency; its other deps are installed above.
    step("Installing pdfplumber", INSTALL_SECONDS)
    await micropip.install("pdfplumber>=0.11.9", deps=False)
    step("Installing markitdown", INSTALL_SECONDS)
    await micropip.install(wheel_url, deps=False)

    _install_stubs()

    # Importing markitdown would pull these in anyway, but with no progress.
    for module, seconds in IMPORT_SECONDS.items():
        step(f"Loading {module.split('.')[0]}", seconds)
        try:
            importlib.import_module(module)
        except ImportError:
            pass  # MarkItDown reports a missing optional dependency when it's used.

    step("Loading markitdown", MARKITDOWN_IMPORT_SECONDS)
    from markitdown import MarkItDown, StreamInfo, __version__

    _md = MarkItDown()
    return __version__


def convert(filename: str, data) -> dict:
    """Convert a file's bytes (a JS Uint8Array or bytes) to Markdown."""
    if hasattr(data, "to_py"):
        data = data.to_py()
    stream_info = StreamInfo(
        filename=filename, extension=os.path.splitext(filename)[1] or None
    )
    result = _md.convert_stream(io.BytesIO(bytes(data)), stream_info=stream_info)
    return {"title": result.title, "markdown": result.markdown}
