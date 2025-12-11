#!/bin/bash
set -eu
# start only backend for local dev
pip install -r backend/requirements.txt
export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/code_analysis
uvicorn backend.main:app --reload
