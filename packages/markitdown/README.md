# MarkItDown

> [!TIP]
> MarkItDown is a Python package and command-line utility for converting various files to Markdown (e.g., for indexing, text analysis, etc).
>
> For more information, see the project [README.md](https://github.com/jwlei/markitdownweb) on GitHub.

> [!IMPORTANT]
> MarkItDown performs I/O with the privileges of the current process. Like open() or requests.get(), it will access resources that the process itself can access. Sanitize your inputs in untrusted environments, and call the narrowest `convert_*` function needed for your use case (e.g., `convert_stream()`, or `convert_local()`).

## Installation

From PyPI:

```bash
pip install 'markitdown[all]'
```

From source:

```bash
git clone git@github.com:jwlei/markitdownweb.git
cd markitdownweb
pip install -e 'packages/markitdown[all]'
```

## Usage

### Command-Line

```bash
markitdown path-to-file.pdf > document.md
```

### Python API

```python
from markitdown import MarkItDown

md = MarkItDown()
result = md.convert("test.xlsx")
print(result.markdown)
```
