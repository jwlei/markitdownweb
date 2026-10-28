"""
Assemble the static site into _site/ for GitHub Pages.

Builds the MarkItDown wheel from packages/markitdown and copies the web
front end next to it. Serve locally with:

    python web/build.py
    python -m http.server -d _site
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
OUT = ROOT / "_site"

STATIC_FILES = [
    "index.html",
    "app.js",
    "worker.js",
    "markitdown_web.py",
    "favicon.svg",
    "og.png",
    "sitemap.xml",
]


def main() -> None:
    shutil.rmtree(OUT, ignore_errors=True)
    wheels = OUT / "wheels"

    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            "--no-deps",
            "--wheel-dir",
            str(wheels),
            str(ROOT / "packages" / "markitdown"),
        ],
        check=True,
    )
    wheel = next(wheels.glob("markitdown-*.whl"))

    for name in STATIC_FILES:
        shutil.copy2(WEB / name, OUT / name)
    (OUT / "wheel.json").write_text(json.dumps({"wheel": f"wheels/{wheel.name}"}))

    print(f"Built {OUT} with {wheel.name}")


if __name__ == "__main__":
    main()
