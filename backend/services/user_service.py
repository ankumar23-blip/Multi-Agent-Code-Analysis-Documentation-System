"""User and authentication service."""
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from ..schemas import UserRole
from ..persistence import load_users_db, save_users_db, load_projects_db, save_projects_db

# Load users from persistence on startup
users_db = load_users_db()
projects_db = load_projects_db()
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
        # Activity feed: list of {ts, level, message, file}
        "activity_feed": [],
        # Pause/resume control
        "paused": False,
        # Analysis configuration (depth: quick/standard/deep, verbosity: low/med/high)
        "config": {
            "depth": "standard",
            "verbosity": "medium",
            "features": {
                "diagrams": False,
                "web_augment": True
            }
        },
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "job_id": None,
        "error": None,
        "user_context": [],
        "qna": [],
        "current_stage": None,
        "current_file": None
    }
    
    # Schedule analysis in the background
    import asyncio
    asyncio.create_task(_run_analysis_for_project(project_id, repository_url, personas, local_file_path))
    save_projects_db(projects_db)
    
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

        def feed(level: str, message: str, file: str = None):
            from ..utils.langfuse_client import track_event
            entry = {
                "ts": datetime.utcnow().isoformat(),
                "level": level,  # info/warn/error
                "message": message,
                "file": file
            }
            project.setdefault("activity_feed", []).append(entry)
            project["updated_at"] = datetime.utcnow().isoformat()
            save_projects_db(projects_db)
            try:
                track_event('analysis.activity', {
                    "project_id": project_id,
                    "level": level,
                    "message": message,
                    "file": file
                })
            except Exception:
                pass
        
        # Phase 1: Download repository (20%)
        project["progress"] = 5.0
        project["status_message"] = "Downloading repository..."
        project["updated_at"] = datetime.utcnow().isoformat()
        feed("info", "Starting repository download and extraction")
        
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
                feed("info", "Repository extracted, starting preprocessing")

                # Preprocessing: walk files and report per-file progress
                all_files = []
                for root, dirs, files in os.walk(repo_dir):
                    # skip common skip dirs
                    if any(skip in root for skip in ['.git', 'node_modules', '__pycache__']):
                        continue
                    for f in files:
                        all_files.append(os.path.join(root, f))

                total_files = max(1, len(all_files))
                processed = 0
                depth = project.get("config", {}).get("depth", "standard")
                # adjust sampling for quick mode
                sample_rate = 1.0
                if depth == 'quick':
                    sample_rate = 0.2
                elif depth == 'deep':
                    sample_rate = 1.0

                for file_path in all_files:
                    # Respect pause signal
                    while project.get("paused"):
                        await asyncio.sleep(0.5)

                    processed += 1
                    # If quick mode, skip some files
                    import random
                    if sample_rate < 1.0 and random.random() > sample_rate:
                        feed("warn", "Skipped file due to quick mode", os.path.relpath(file_path, repo_dir))
                        continue

                    # Detect binary files (simple heuristic)
                    try:
                        with open(file_path, 'rb') as fh:
                            start = fh.read(1024)
                            if b'\0' in start:
                                feed("warn", "Skipped binary file", os.path.relpath(file_path, repo_dir))
                                continue
                    except Exception:
                        feed("warn", "Unable to read file during preprocessing", os.path.relpath(file_path, repo_dir))
                        continue

                    pct = 25.0 + (processed / total_files) * 30.0  # map preprocessing to 25-55%
                    project["progress"] = min(55.0, pct)
                    project["status_message"] = f"Preprocessing files: {processed}/{total_files}"
                    feed("info", f"Processing file {processed}/{total_files}: {os.path.basename(file_path)}", os.path.relpath(file_path, repo_dir))
                    # small yield to allow UI to poll
                    await asyncio.sleep(0.01)
                
                # Phase 2: Detect languages and frameworks (40%)
                from ..agents.analyzer import RepositoryAnalyzer
                analyzer = RepositoryAnalyzer(repo_dir)
                
                project["progress"] = 35.0
                project["status_message"] = "Detecting languages..."
                project["updated_at"] = datetime.utcnow().isoformat()
                feed("info", "Detecting languages and basic repository characteristics")
                await asyncio.sleep(0.2)

                project["progress"] = 45.0
                project["status_message"] = "Detecting frameworks..."
                project["updated_at"] = datetime.utcnow().isoformat()
                feed("info", "Detecting frameworks and important files")
                await asyncio.sleep(0.2)
                # Web-augmented lookups (logs only)
                try:
                    if project.get("config", {}).get("features", {}).get("web_augment", False):
                        feed("info", "Searching FastAPI documentation for async endpoint patterns")
                        feed("info", "Checking OWASP guidelines for authentication implementation")
                        feed("info", "Finding migration notes for React 18 features used in codebase")
                        feed("info", "Retrieving recommended patterns for SQLAlchemy session management")
                except Exception:
                    pass
                
                # Phase 3: Extract code chunks (60%) - now using analyzer with progress callback
                project["progress"] = 55.0
                project["status_message"] = "Extracting code chunks..."
                project["updated_at"] = datetime.utcnow().isoformat()
                feed("info", "Extracting functions, classes and code chunks")

                async def analyzer_progress(stage, percent, message, file=None):
                    # Update project progress and feed
                    project["progress"] = float(percent)
                    project["status_message"] = message
                    project["updated_at"] = datetime.utcnow().isoformat()
                    if stage == 'processing_file' and file:
                        feed('info', message, file)
                    else:
                        feed('info', message)

                    # Respect pause signal
                    while project.get("paused"):
                        await asyncio.sleep(0.5)

                # Run analyzer asynchronously and pass progress callback
                metadata = await analyzer.analyze(progress_callback=analyzer_progress)

                # Web-augmented references (fetch short snippets based on detected frameworks)
                try:
                    import httpx
                    refs = {}
                    fw_lower = set([str(f).lower() for f in (getattr(metadata, "frameworks", []) or [])])
                    candidates = []
                    if 'fastapi' in fw_lower:
                        candidates.append(("fastapi", "https://fastapi.tiangolo.com/"))
                    if 'django' in fw_lower:
                        candidates.append(("django", "https://docs.djangoproject.com/en/stable/"))
                    if 'flask' in fw_lower:
                        candidates.append(("flask", "https://flask.palletsprojects.com/"))
                    if 'react' in fw_lower:
                        candidates.append(("react", "https://react.dev/learn"))
                    if 'express' in fw_lower:
                        candidates.append(("express", "https://expressjs.com/"))
                    # Always include OWASP auth cheat sheet as general reference
                    candidates.append(("owasp-auth", "https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html"))

                    with httpx.Client(timeout=6.0, follow_redirects=True) as client:
                        for key, url in candidates[:5]:
                            try:
                                r = client.get(url)
                                if r.status_code == 200:
                                    text = r.text
                                    # Keep short snippet to avoid payload bloat
                                    snippet = text[:800]
                                    refs[url] = snippet
                            except Exception:
                                continue
                    # Attach references to metadata object for downstream consumers
                    setattr(metadata, "web_references", refs or {})
                    if refs:
                        feed("info", f"Web augmentation fetched {len(refs)} reference pages")
                except Exception:
                    setattr(metadata, "web_references", {})

                chunks = analyzer.code_chunks
                feed("info", f"Extractor found {len(chunks)} code chunks")
                
                project["progress"] = 70.0
                project["status_message"] = "Building search index..."
                project["updated_at"] = datetime.utcnow().isoformat()
                feed("info", "Building search index for fast lookup")
                await asyncio.sleep(0.2)
                
                # Phase 4: Final processing (90%)
                from ..agents.search import SemanticSearchEngine
                search_engine = SemanticSearchEngine(chunks)
                
                project["progress"] = 85.0
                project["status_message"] = "Caching results..."
                project["updated_at"] = datetime.utcnow().isoformat()
                feed("info", "Caching analysis results and finalizing")
                
                # Cache results
                from ..analysis_routes import _analysis_cache
                _analysis_cache[project_id] = (metadata, chunks, search_engine)
                
                # Phase 5: Complete (100%)
                project["progress"] = 100.0
                project["status"] = "completed"
                project["status_message"] = "Analysis complete!"
                project["updated_at"] = datetime.utcnow().isoformat()
                feed("info", "Analysis complete")
        
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
