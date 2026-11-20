"""Vercel's entry point for the Python API (src/api.py).

Vercel imports `app` from this file (pyproject.toml tells it to: [tool.vercel]
entrypoint = "index:app"). It lives at the top of the project, not in src/, because
src/ also holds app.py, the Streamlit app, and Vercel would otherwise try that one.

The API's modules live in src/ and import each other by plain name ("import data",
"import mvp"), the same way they do when you run uvicorn with --app-dir src. So we add
src/ to Python's search path first, then import the FastAPI app from src/api.py.

Running locally doesn't use this file at all: keep using
    py -m uvicorn api:app --app-dir src --reload --port 8000
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from api import app  # noqa: E402,F401  (must come after the sys.path line; Vercel looks for `app`)
