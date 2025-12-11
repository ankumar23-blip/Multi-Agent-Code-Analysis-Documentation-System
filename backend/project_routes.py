"""Project management routes."""
from fastapi import APIRouter, HTTPException, Header, UploadFile, File
from typing import Optional, List
from .schemas import (
    ProjectCreateRequest, ProjectCreateResponse, ProjectInfo
)
from .services.user_service import (
    create_project, get_project, get_user_projects,
    verify_token
)
from .utils.file_validator import validate_zip_file

router = APIRouter(prefix="/projects", tags=["projects"])


def get_current_user_id(authorization: Optional[str] = Header(None)) -> str:
    """Extract user_id from Bearer token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    
    token = authorization.split(" ")[1]
    token_data = verify_token(token)
    
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return token_data["user_id"]


@router.post("/", response_model=ProjectCreateResponse)
async def create_project_handler(
    payload: ProjectCreateRequest,
    authorization: Optional[str] = Header(None)
):
    """Create a new analysis project with GitHub URL."""
    try:
        user_id = get_current_user_id(authorization)
        
        if not payload.repository_url:
            raise ValueError("Repository URL is required")
        
        project = await create_project(
            user_id=user_id,
            name=payload.name,
            repository_url=payload.repository_url,
            personas=[p.value for p in payload.personas],
            description=payload.description
        )
        
        return ProjectCreateResponse(
            project_id=project["project_id"],
            name=project["name"],
            created_at=project["created_at"],
            status=project["status"]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Project creation failed: {str(e)}")


@router.post("/upload")
async def upload_project(
    file: UploadFile = File(...),
    name: Optional[str] = Header(None),
    personas: Optional[str] = Header("sde"),
    authorization: Optional[str] = Header(None)
):
    """Upload a ZIP file for analysis."""
    import tempfile
    import os
    import shutil
    
    try:
        user_id = get_current_user_id(authorization)
        
        if not name:
            raise ValueError("Project name is required (via 'name' header)")
        
        # Read file content
        content = await file.read()
        
        # Save uploaded file to a persistent location (not temp)
        upload_dir = os.path.join(os.getcwd(), "uploads")
        os.makedirs(upload_dir, exist_ok=True)
        
        # Generate unique filename
        import uuid
        unique_name = f"{uuid.uuid4()}_{file.filename}"
        file_path = os.path.join(upload_dir, unique_name)
        
        # Write file
        with open(file_path, 'wb') as f:
            f.write(content)
        
        try:
            # Validate ZIP
            print(f"[UPLOAD] Validating ZIP file: {file_path}")
            print(f"[UPLOAD] File size: {len(content)} bytes")
            is_valid, error_msg = validate_zip_file(file_path, len(content))
            print(f"[UPLOAD] Validation result: is_valid={is_valid}, error={error_msg}")
            
            if not is_valid:
                # Clean up if validation fails
                if os.path.exists(file_path):
                    os.remove(file_path)
                raise ValueError(error_msg)
            
            # Parse personas from comma-separated header
            persona_list = [p.strip() for p in personas.split(',')]
            
            # Create project with ZIP file path (pass as local_file_path, not URL)
            project = await create_project(
                user_id=user_id,
                name=name,
                repository_url=f"Uploaded ZIP: {file.filename}",  # Show actual zip filename
                personas=persona_list,
                description=None,
                local_file_path=file_path  # Pass actual file path here
            )
            
            return {
                "project_id": project["project_id"],
                "name": project["name"],
                "status": project["status"],
                "message": "Project created and analysis started"
            }
        
        except ValueError as e:
            # Clean up on error
            if os.path.exists(file_path):
                os.remove(file_path)
            raise
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/", response_model=List[ProjectInfo])
async def list_user_projects(authorization: Optional[str] = Header(None)):
    """List all projects for the current user."""
    try:
        user_id = get_current_user_id(authorization)
        projects = await get_user_projects(user_id)
        return [ProjectInfo(**p) for p in projects]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch projects: {str(e)}")


@router.get("/{project_id}", response_model=ProjectInfo)
async def get_project_handler(
    project_id: str,
    authorization: Optional[str] = Header(None)
):
    """Get project details."""
    try:
        user_id = get_current_user_id(authorization)
        project = await get_project(project_id)
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Check ownership (for now, allow admin to view any project)
        if project["owner_id"] != user_id:
            # TODO: check if user is admin
            pass
        
        return ProjectInfo(**project)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch project: {str(e)}")


@router.post("/{project_id}/configure")
async def configure_project(project_id: str, config: dict, authorization: Optional[str] = Header(None)):
    """Update analysis configuration for a project (depth, verbosity, features).

    Example body: {"depth":"deep","verbosity":"high","features":{"diagrams":true}}
    """
    try:
        user_id = get_current_user_id(authorization)
        project = await get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        if project["owner_id"] != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        # Merge config
        project.setdefault("config", {}).update(config)
        project["updated_at"] = __import__("datetime").datetime.utcnow().isoformat()
        project.setdefault("activity_feed", []).append({"ts": __import__("datetime").datetime.utcnow().isoformat(), "level": "info", "message": f"Analysis configuration updated: {config}"})
        return {"project_id": project_id, "config": project.get("config")}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
