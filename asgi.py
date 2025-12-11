"""ASGI entrypoint for uvicorn.

This file is at the project root to make running uvicorn simpler:
  python -m uvicorn asgi:app --reload
"""
from backend.main import app

__all__ = ['app']
