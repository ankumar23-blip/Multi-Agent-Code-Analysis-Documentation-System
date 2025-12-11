"""Admin routes: users/projects management and basic analytics."""
from fastapi import APIRouter, HTTPException, Header
from typing import Optional, Dict, Any
from .services.user_service import verify_token, hash_password
from .persistence import load_users_db, save_users_db, load_projects_db, save_projects_db

router = APIRouter(prefix="/admin", tags=["admin"])


def require_admin(authorization: Optional[str]) -> Dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    token = authorization.split(" ")[1]
    token_data = verify_token(token)
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid token")
    if str(token_data.get("role", "")).lower() != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return token_data


@router.get("/users")
async def list_users(authorization: Optional[str] = Header(None)):
    require_admin(authorization)
    users = load_users_db()
    # Hide password hashes in response
    safe = []
    for email, data in users.items():
        d = {k: v for k, v in data.items() if k != "password"}
        safe.append(d)
    return {"total": len(safe), "users": safe}


@router.post("/users")
async def create_user(
    body: Dict[str, Any],
    authorization: Optional[str] = Header(None)
):
    """
    Create a user (admin-only). Body: {email, password, name, role}
    """
    require_admin(authorization)
    users = load_users_db()
    email = (body.get("email") or "").strip().lower()
    password = (body.get("password") or "").strip()
    name = (body.get("name") or "").strip()
    role = (body.get("role") or "user").strip().lower()
    if not email or not password or not name:
        raise HTTPException(status_code=400, detail="Missing email/password/name")
    if email in users:
        raise HTTPException(status_code=400, detail="User already exists")
    uid = __import__("uuid").uuid4().hex
    users[email] = {
        "user_id": uid,
        "email": email,
        "password": hash_password(password),
        "name": name,
        "role": role,
        "created_at": __import__("datetime").datetime.utcnow().isoformat()
    }
    save_users_db(users)
    return {"status": "created", "user_id": uid}


@router.patch("/users/{email}")
async def update_user(
    email: str,
    body: Dict[str, Any],
    authorization: Optional[str] = Header(None)
):
    require_admin(authorization)
    users = load_users_db()
    key = email.strip().lower()
    if key not in users:
        raise HTTPException(status_code=404, detail="User not found")
    if "name" in body:
        users[key]["name"] = str(body["name"])
    if "role" in body:
        users[key]["role"] = str(body["role"]).lower()
    if "password" in body and body["password"]:
        users[key]["password"] = hash_password(str(body["password"]))
    save_users_db(users)
    return {"status": "updated"}


@router.delete("/users/{email}")
async def delete_user(email: str, authorization: Optional[str] = Header(None)):
    require_admin(authorization)
    users = load_users_db()
    key = email.strip().lower()
    if key not in users:
        raise HTTPException(status_code=404, detail="User not found")
    users.pop(key)
    save_users_db(users)
    return {"status": "deleted"}


@router.get("/projects")
async def list_projects(authorization: Optional[str] = Header(None)):
    require_admin(authorization)
    projects = load_projects_db()
    return {"total": len(projects), "projects": list(projects.values())}


@router.patch("/projects/{project_id}")
async def update_project(project_id: str, body: Dict[str, Any], authorization: Optional[str] = Header(None)):
    require_admin(authorization)
    projects = load_projects_db()
    proj = projects.get(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    # Allow updating status, name, description
    for f in ["status", "name", "description", "progress", "status_message"]:
        if f in body:
            proj[f] = body[f]
    proj["updated_at"] = __import__("datetime").datetime.utcnow().isoformat()
    projects[project_id] = proj
    save_projects_db(projects)
    return {"status": "updated", "project": proj}


@router.delete("/projects/{project_id}")
async def delete_project(project_id: str, authorization: Optional[str] = Header(None)):
    require_admin(authorization)
    projects = load_projects_db()
    if project_id not in projects:
        raise HTTPException(status_code=404, detail="Project not found")
    projects.pop(project_id)
    save_projects_db(projects)
    return {"status": "deleted"}


@router.get("/analytics")
async def analytics(authorization: Optional[str] = Header(None)):
    """
    Basic analytics: total users, total projects, active projects, completion rate.
    """
    require_admin(authorization)
    users = load_users_db()
    projects = load_projects_db()
    total_users = len(users)
    total_projects = len(projects)
    active = sum(1 for p in projects.values() if p.get("status") == "analyzing")
    completed = sum(1 for p in projects.values() if p.get("status") == "completed")
    failed = sum(1 for p in projects.values() if p.get("status") == "failed")
    completion_rate = (completed / total_projects) if total_projects else 0.0
    return {
        "users": total_users,
        "projects": total_projects,
        "active_projects": active,
        "completed_projects": completed,
        "failed_projects": failed,
        "completion_rate": round(completion_rate, 3)
    }
