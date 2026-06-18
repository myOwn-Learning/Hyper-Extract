# Installation

Hyper-Extract requires **Python 3.11+**.

---

## Install as CLI Tool

If you want to use the `he` command from anywhere:

=== "uv (recommended)"

    ```bash
    uv tool install hyperextract
    ```

=== "pipx"

    ```bash
    pipx install hyperextract
    ```

---

## Install as Python Library

If you want to use Hyper-Extract in your Python code:

=== "uv (recommended)"

    ```bash
    uv pip install hyperextract
    ```

=== "pip"

    ```bash
    pip install hyperextract
    ```

---

## Verify Installation

=== "CLI"

    ```bash
    he --version
    ```

    You should see something like:

    ```
    Hyper-Extract CLI version 0.1.3.dev0
    ```

=== "Python"

    ```python
    import hyperextract
    print(hyperextract.__version__)
    ```

---

## Development Installation

If you want to contribute or modify the source code:

```bash
# Clone the repository
git clone https://github.com/myOwn-Learning/Hyper-Extract.git
cd hyper-extract

# Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

---

## What's Next?

- [:octicons-arrow-right-24: CLI Quickstart](cli-quickstart.md) — Your first extraction from the terminal
- [:octicons-arrow-right-24: Python Quickstart](python-quickstart.md) — Your first extraction with Python
