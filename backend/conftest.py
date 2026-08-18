"""Root test bootstrap.

Pytest imports this before test modules and ``tests/conftest.py``.
It loads ``.env.test`` before app imports that read settings at import
time. ``pythonpath = ["app"]`` in ``pyproject.toml`` exposes the app
packages without per-file ``sys.path`` mutation.
"""

from pathlib import Path

from dotenv import load_dotenv

# Load test environment variables before any app module is imported.
load_dotenv(dotenv_path=Path(__file__).parent / ".env.test")
