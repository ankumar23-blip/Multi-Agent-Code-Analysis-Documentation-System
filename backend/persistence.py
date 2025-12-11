"""Persistence layer for user data."""
import json
import os
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent.parent / "data"
USERS_FILE = DATA_DIR / "users.json"
PROJECTS_FILE = DATA_DIR / "projects.json"


def ensure_data_dir():
    """Ensure data directory exists."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_users_db():
    """Load users from persistence."""
    ensure_data_dir()
    
    if USERS_FILE.exists():
        try:
            with open(USERS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"[PERSIST] Error loading users: {e}")
            return {}
    return {}


def save_users_db(users_db):
    """Save users to persistence."""
    ensure_data_dir()
    
    try:
        with open(USERS_FILE, 'w') as f:
            json.dump(users_db, f, indent=2)
    except Exception as e:
        print(f"[PERSIST] Error saving users: {e}")


def load_projects_db():
    """Load projects from persistence."""
    ensure_data_dir()
    if PROJECTS_FILE.exists():
        try:
            with open(PROJECTS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"[PERSIST] Error loading projects: {e}")
            return {}
    return {}


def save_projects_db(projects_db):
    """Save projects to persistence."""
    ensure_data_dir()
    try:
        with open(PROJECTS_FILE, 'w') as f:
            json.dump(projects_db, f, indent=2)
    except Exception as e:
        print(f"[PERSIST] Error saving projects: {e}")
