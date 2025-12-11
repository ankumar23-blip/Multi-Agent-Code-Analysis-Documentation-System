"""User and authentication service."""
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from ..schemas import UserRole
from ..persistence import load_users_db, save_users_db

# Load users from persistence on startup
users_db = load_users_db()
projects_db = {}
sessions_db = {}

SECRET_KEY = "your-secret-key-change-in-production"  # TODO: move to env var
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def hash_password(password: str) -> str:
    """Hash a password using SHA256 (for demo; use bcrypt in production)."""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return hash_password(plain_password) == hashed_password


def create_access_token(user_id: str, email: str, role: UserRole, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token."""
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    expire = datetime.utcnow() + expires_delta
    to_encode = {
        "sub": user_id,
        "email": email,
        "role": role.value,
        "exp": expire
    }
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> dict:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        email = payload.get("email")
        role = payload.get("role")
        if user_id is None or email is None:
            return None
        return {"user_id": user_id, "email": email, "role": role}
    except JWTError:
        return None


async def signup(email: str, password: str, name: str) -> dict:
    """Create a new user account."""
    if email in users_db:
        raise ValueError("User already exists")
    
    user_id = str(uuid.uuid4())
    hashed_pwd = hash_password(password)
    
    users_db[email] = {
        "user_id": user_id,
        "email": email,
        "password": hashed_pwd,
        "name": name,
        "role": UserRole.USER.value,
        "created_at": datetime.utcnow().isoformat()
    }
    
    # Persist to disk
    save_users_db(users_db)
    print(f"[AUTH] User registered: {email}")
    
    return {
        "user_id": user_id,
        "email": email,
        "name": name,
        "role": UserRole.USER.value
    }


async def login(email: str, password: str) -> dict:
    """Authenticate a user and return a token."""
    user = users_db.get(email)
    if not user or not verify_password(password, user["password"]):
        raise ValueError("Invalid credentials")
    
    token = create_access_token(
        user_id=user["user_id"],
        email=user["email"],
        role=UserRole(user["role"])
    )
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user["user_id"],
        "role": user["role"]
    }


async def get_user_by_id(user_id: str) -> Optional[dict]:
    """Fetch a user by user_id."""
    for user in users_db.values():
        if user["user_id"] == user_id:
            return user
    return None


async def get_user_projects(user_id: str) -> list:
    """Get all projects owned by a user."""
    return [p for p in projects_db.values() if p["owner_id"] == user_id]


async def create_project(user_id: str, name: str, repository_url: str, personas: list, description: str = None, local_file_path: str = None) -> dict:
    """Create a new project and trigger analysis.
    
    The project is created with status 'analyzing' and the analysis
    pipeline is scheduled to run asynchronously.
    
    Args:
        local_file_path: For ZIP uploads, the actual file path on disk
    """
    from ..utils.file_validator import validate_github_url
    
    # Validate GitHub URL if provided (skip for uploaded ZIP files)
    if repository_url and not local_file_path:
        is_valid, error_msg = validate_github_url(repository_url)
        if not is_valid:
            raise ValueError(f"Invalid repository: {error_msg}")
    
    project_id = str(uuid.uuid4())
    
    projects_db[project_id] = {
        "project_id": project_id,
        "owner_id": user_id,
        "name": name,
        "repository_url": repository_url,
        "local_file_path": local_file_path,  # Store actual file path for ZIPs
        "personas": personas,
        "description": description,
        "status": "analyzing",  # Start as analyzing
        "progress": 0.0,
        "status_message": "Initializing analysis...",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "job_id": None,
        "error": None
    }
    
    # Schedule analysis in the background
    import asyncio
    asyncio.create_task(_run_analysis_for_project(project_id, repository_url, personas, local_file_path))
    
    return projects_db[project_id]


async def _run_analysis_for_project(project_id: str, repository_url: str, personas: list, local_file_path: str = None):
    """Run analysis pipeline for a project (background task)."""
    try:
        import asyncio
        import httpx
        import tempfile
        import zipfile
        import os
        
        project = projects_db[project_id]
        
        # Phase 1: Download repository (20%)
        project["progress"] = 5.0
        project["status_message"] = "Downloading repository..."
        project["updated_at"] = datetime.utcnow().isoformat()
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                zip_path = None
                
                # If this is a ZIP upload, use the local file
                if local_file_path:
                    zip_path = local_file_path
                    project["progress"] = 15.0
                    project["status_message"] = "Extracting files..."
                    project["updated_at"] = datetime.utcnow().isoformat()
                # Otherwise download from GitHub
                elif "github.com" in repository_url:
                    parts = repository_url.rstrip('/').split('/')
                    owner, repo = parts[-2], parts[-1]
                    archive_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/main.zip"
                    
                    # Download
                    response = httpx.get(archive_url, timeout=60, follow_redirects=True)
                    if response.status_code == 404:
                        archive_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/master.zip"
                        response = httpx.get(archive_url, timeout=60, follow_redirects=True)
                    
                    if response.status_code != 200:
                        raise ValueError(f"Failed to download (HTTP {response.status_code})")
                    
                    zip_path = os.path.join(temp_dir, "repo.zip")
                    with open(zip_path, 'wb') as f:
                        f.write(response.content)
                    
                    project["progress"] = 15.0
                    project["status_message"] = "Extracting files..."
                    project["updated_at"] = datetime.utcnow().isoformat()
                else:
                    raise ValueError(f"Unsupported repository URL format: {repository_url}")
                
                extract_path = os.path.join(temp_dir, "extracted")
                with zipfile.ZipFile(zip_path, 'r') as zf:
                    zf.extractall(extract_path)
                
                # Find repo directory
                repo_dir = extract_path
                subdirs = [d for d in os.listdir(extract_path) if os.path.isdir(os.path.join(extract_path, d))]
                if len(subdirs) == 1:
                    repo_dir = os.path.join(extract_path, subdirs[0])
                
                project["progress"] = 25.0
                project["status_message"] = "Analyzing code structure..."
                project["updated_at"] = datetime.utcnow().isoformat()
                
                # Phase 2: Detect languages and frameworks (40%)
                from ..agents.analyzer import RepositoryAnalyzer
                analyzer = RepositoryAnalyzer(repo_dir)
                
                project["progress"] = 35.0
                project["status_message"] = "Detecting languages..."
                project["updated_at"] = datetime.utcnow().isoformat()
                await asyncio.sleep(0.5)
                
                project["progress"] = 45.0
                project["status_message"] = "Detecting frameworks..."
                project["updated_at"] = datetime.utcnow().isoformat()
                await asyncio.sleep(0.5)
                
                # Phase 3: Extract code chunks (60%)
                project["progress"] = 55.0
                project["status_message"] = "Extracting code chunks..."
                project["updated_at"] = datetime.utcnow().isoformat()
                
                metadata = analyzer.analyze()
                chunks = analyzer.code_chunks
                
                project["progress"] = 70.0
                project["status_message"] = "Building search index..."
                project["updated_at"] = datetime.utcnow().isoformat()
                await asyncio.sleep(0.5)
                
                # Phase 4: Final processing (90%)
                from ..agents.search import SemanticSearchEngine
                search_engine = SemanticSearchEngine(chunks)
                
                project["progress"] = 85.0
                project["status_message"] = "Caching results..."
                project["updated_at"] = datetime.utcnow().isoformat()
                
                # Cache results
                from ..analysis_routes import _analysis_cache
                _analysis_cache[project_id] = (metadata, chunks, search_engine)
                
                # Phase 5: Complete (100%)
                project["progress"] = 100.0
                project["status"] = "completed"
                project["status_message"] = "Analysis complete!"
                project["updated_at"] = datetime.utcnow().isoformat()
        
        except Exception as analyze_err:
            project["progress"] = 100.0
            project["status"] = "failed"
            project["error"] = str(analyze_err)
            project["status_message"] = f"Error: {str(analyze_err)}"
            project["updated_at"] = datetime.utcnow().isoformat()
    
    except Exception as e:
        project = projects_db.get(project_id)
        if project:
            project["status"] = "failed"
            project["error"] = str(e)
            project["status_message"] = f"Critical error: {str(e)}"
            project["progress"] = 0.0
            project["updated_at"] = datetime.utcnow().isoformat()


async def get_project(project_id: str) -> Optional[dict]:
    """Fetch a project by ID."""
    return projects_db.get(project_id)


async def update_project_status(project_id: str, status: str) -> dict:
    """Update project status."""
    if project_id not in projects_db:
        raise ValueError("Project not found")
    
    projects_db[project_id]["status"] = status
    projects_db[project_id]["updated_at"] = datetime.utcnow().isoformat()
    return projects_db[project_id]
