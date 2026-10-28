"""
Browser bootstrap for MarkItDown running under Pyodide.

Installs the dependencies that work in WebAssembly, stubs out the two that
cannot load there (magika, pypdfium2), then installs the MarkItDown wheel
built from this repository.
"""

import io
import os
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


async def setup(wheel_url: str) -> str:
    global _md, StreamInfo

    await micropip.install(DEPENDENCIES)
    # Skip pdfplumber's pypdfium2 dependency; its other deps are installed above.
    await micropip.install("pdfplumber>=0.11.9", deps=False)
    await micropip.install(wheel_url, deps=False)

    _install_stubs()

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
