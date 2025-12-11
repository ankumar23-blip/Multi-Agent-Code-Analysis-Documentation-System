"""Analysis routes for code understanding and discovery."""
from fastapi import APIRouter, HTTPException, Header
from typing import Optional, List
from .schemas import UserRole
from .services.user_service import verify_token, get_project
from .agents.analyzer import RepositoryAnalyzer, CodeChunk
from .agents.search import SemanticSearchEngine

router = APIRouter(prefix="/analysis", tags=["analysis"])

# Cache for analyzed projects (project_id -> (metadata, chunks, search_engine))
_analysis_cache = {}


def get_current_user_id(authorization: Optional[str] = Header(None)) -> str:
    """Extract user_id from Bearer token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    
    token = authorization.split(" ")[1]
    token_data = verify_token(token)
    
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return token_data["user_id"]


@router.get("/{project_id}/metadata")
async def get_repo_metadata(
    project_id: str,
    authorization: Optional[str] = Header(None)
):
    """Get repository metadata and intelligence."""
    try:
        user_id = get_current_user_id(authorization)
        project = await get_project(project_id)
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        if project["owner_id"] != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Return cached metadata if available
        if project_id in _analysis_cache:
            metadata, _, _ = _analysis_cache[project_id]
            return {
                "project_id": project_id,
                "repo_type": metadata.repo_type,
                "frameworks": metadata.frameworks,
                "entry_points": metadata.entry_points,
                "important_files": metadata.important_files,
                "important_files_with_types": metadata.important_files_with_types or [],
                "dependencies": metadata.dependencies,
                "config_files": metadata.config_files,
                "total_files": metadata.total_files,
                "code_files": metadata.code_files,
                "total_code_chunks": metadata.total_code_chunks,
                "confidence_score": metadata.confidence_score
            }
        
        # Analyze the repository in real time
        try:
            import tempfile
            import zipfile
            import httpx
            import os
            
            repo_url = project.get("repository_url", "")
            local_file_path = project.get("local_file_path")
            
            if not repo_url and not local_file_path:
                raise ValueError("No repository URL or file provided")
            
            print(f"[ANALYSIS] Starting analysis for project {project_id}")
            print(f"[ANALYSIS] Repository URL: {repo_url}")
            print(f"[ANALYSIS] Local file path: {local_file_path}")
            
            # Download and extract the repository as ZIP
            with tempfile.TemporaryDirectory() as temp_dir:
                zip_path = None
                
                # Handle uploaded ZIP files (use local path directly)
                if local_file_path:
                    zip_path = local_file_path
                    print(f"[ANALYSIS] Using uploaded ZIP: {zip_path}")
                    if not os.path.exists(zip_path):
                        raise ValueError(f"ZIP file not found: {zip_path}")
                
                # Handle file:// URLs (uploaded ZIPs)
                elif repo_url.startswith("file://"):
                    # Remove file:// prefix and handle Windows paths
                    zip_path = repo_url[7:]  # Remove "file://" prefix
                    # If path starts with single slash on Windows, it's actually a UNC path
                    # Remove leading slash if it's Windows-style absolute path
                    if zip_path.startswith("/") and len(zip_path) > 2 and zip_path[2] == ":":
                        zip_path = zip_path[1:]
                    print(f"[ANALYSIS] Using uploaded ZIP: {zip_path}")
                    if not os.path.exists(zip_path):
                        raise ValueError(f"ZIP file not found: {zip_path}")
                
                # Handle GitHub URLs
                elif "github.com" in repo_url:
                    # Extract owner/repo from URL
                    parts = repo_url.rstrip('/').split('/')
                    owner, repo = parts[-2], parts[-1]
                    # Try main branch first, then master
                    archive_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/main.zip"
                    print(f"[ANALYSIS] Archive URL: {archive_url}")
                    
                    # Download the archive using synchronous client
                    try:
                        print(f"[ANALYSIS] Downloading repository...")
                        response = httpx.get(archive_url, timeout=60, follow_redirects=True)
                        print(f"[ANALYSIS] Download response status: {response.status_code}")
                        
                        if response.status_code == 404:
                            # Try master branch instead
                            archive_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/master.zip"
                            print(f"[ANALYSIS] Trying master branch: {archive_url}")
                            response = httpx.get(archive_url, timeout=60, follow_redirects=True)
                            print(f"[ANALYSIS] Master branch response status: {response.status_code}")
                        
                        if response.status_code != 200:
                            raise ValueError(f"Failed to download repository (HTTP {response.status_code})")
                        
                        zip_path = os.path.join(temp_dir, "repo.zip")
                        with open(zip_path, 'wb') as f:
                            f.write(response.content)
                        print(f"[ANALYSIS] Repository downloaded ({len(response.content)} bytes)")
                    
                    except Exception as download_err:
                        print(f"[ANALYSIS] Download error: {download_err}")
                        raise
                else:
                    raise ValueError(f"Unsupported repository URL format: {repo_url}")
                
                # Extract and analyze
                try:
                    extract_path = os.path.join(temp_dir, "extracted")
                    print(f"[ANALYSIS] Extracting repository...")
                    with zipfile.ZipFile(zip_path, 'r') as zf:
                        zf.extractall(extract_path)
                    
                    # Find the actual repository directory (it's usually wrapped)
                    repo_dir = extract_path
                    subdirs = [d for d in os.listdir(extract_path) if os.path.isdir(os.path.join(extract_path, d))]
                    print(f"[ANALYSIS] Found subdirectories: {subdirs}")
                    
                    if len(subdirs) == 1:
                        repo_dir = os.path.join(extract_path, subdirs[0])
                    
                    print(f"[ANALYSIS] Analyzing repository at: {repo_dir}")
                    
                    # Run analyzer
                    analyzer = RepositoryAnalyzer(repo_dir)
                    metadata = analyzer.analyze()
                    chunks = analyzer.code_chunks  # Get chunks from analyzer
                    search_engine = SemanticSearchEngine(chunks)
                    
                    print(f"[ANALYSIS] Analysis complete: {metadata.repo_type}, {len(chunks)} chunks")
                    
                    # Cache the results
                    _analysis_cache[project_id] = (metadata, chunks, search_engine)
                    
                    return {
                        "project_id": project_id,
                        "repo_type": metadata.repo_type,
                        "frameworks": metadata.frameworks,
                        "entry_points": metadata.entry_points,
                        "important_files": metadata.important_files,
                        "important_files_with_types": metadata.important_files_with_types or [],
                        "dependencies": metadata.dependencies,
                        "config_files": metadata.config_files,
                        "total_files": metadata.total_files,
                        "code_files": metadata.code_files,
                        "total_code_chunks": len(chunks),
                        "confidence_score": metadata.confidence_score
                    }
                
                except Exception as analyze_err:
                    print(f"[ANALYSIS] Analysis error: {analyze_err}")
                    raise
        
        except Exception as e:
            import traceback
            print(f"[ANALYSIS] FAILED: {e}")
            print(traceback.format_exc())
            # Return error instead of falling back to demo data
            raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/chunks")
async def get_code_chunks(
    project_id: str,
    limit: int = 20,
    chunk_type: Optional[str] = None,
    authorization: Optional[str] = Header(None)
):
    """Get code chunks from analyzed repository."""
    try:
        user_id = get_current_user_id(authorization)
        project = await get_project(project_id)
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        if project["owner_id"] != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get chunks from cache or return empty
        if project_id in _analysis_cache:
            _, chunks, _ = _analysis_cache[project_id]
            
            # Filter by chunk type if provided
            if chunk_type:
                chunks = [c for c in chunks if c.chunk_type == chunk_type]
            
            # Convert chunks to dict format
            chunk_list = []
            for chunk in chunks[:limit]:
                chunk_list.append({
                    "chunk_id": f"{chunk.file_path}:{chunk.start_line}",
                    "file_path": chunk.file_path,
                    "chunk_type": chunk.chunk_type,
                    "name": chunk.name,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                    "language": chunk.language,
                    "content": chunk.content
                })
            
            return {
                "project_id": project_id,
                "total_chunks": len(chunks),
                "chunks": chunk_list
            }
        
        # Return empty if not cached yet
        return {
            "project_id": project_id,
            "total_chunks": 0,
            "chunks": [],
            "message": "Analysis not yet complete"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/search")
async def search_code(
    project_id: str,
    query: str,
    limit: int = 10,
    authorization: Optional[str] = Header(None)
):
    """Search for relevant code chunks."""
    try:
        user_id = get_current_user_id(authorization)
        project = await get_project(project_id)
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        if project["owner_id"] != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get search engine from cache
        if project_id in _analysis_cache:
            _, chunks, search_engine = _analysis_cache[project_id]
            
            # Perform semantic search
            results = search_engine.search(query, limit=limit)
            
            # Format results
            search_results = []
            for result in results:
                search_results.append({
                    "chunk_id": f"{result['file_path']}:{result['start_line']}",
                    "file_path": result['file_path'],
                    "name": result['name'],
                    "relevance_score": result['score'],
                    "preview": result['content'][:200] + "..." if len(result['content']) > 200 else result['content']
                })
            
            return {
                "query": query,
                "total_results": len(search_results),
                "results": search_results
            }
        
        # Return empty if not cached
        return {
            "query": query,
            "total_results": 0,
            "results": [],
            "message": "Analysis not yet complete"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/analyze")
async def trigger_analysis(
    project_id: str,
    authorization: Optional[str] = Header(None)
):
    """Trigger intelligent preprocessing of repository."""
    try:
        user_id = get_current_user_id(authorization)
        project = await get_project(project_id)
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        if project["owner_id"] != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        return {
            "project_id": project_id,
            "status": "analysis_started",
            "message": "Repository analysis in progress. System is identifying structure and extracting code chunks.",
            "estimated_chunks": 150
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/persona-analysis/{persona}")
async def get_persona_analysis(
    project_id: str,
    persona: str,
    authorization: Optional[str] = Header(None)
):
    """Get persona-specific analysis (SDE or PM).
    
    Args:
        project_id: The project to analyze
        persona: 'sde' or 'pm'
    """
    try:
        user_id = get_current_user_id(authorization)
        project = await get_project(project_id)
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        if project["owner_id"] != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        persona = persona.lower()
        if persona not in ['sde', 'pm']:
            raise HTTPException(status_code=400, detail="Persona must be 'sde' or 'pm'")
        
        # Check project status
        if project.get("status") != "completed":
            raise HTTPException(status_code=202, detail="Analysis not yet complete. Please wait.")
        
        print(f"[PERSONA] Checking cache for project {project_id}")
        print(f"[PERSONA] Current cache keys: {list(_analysis_cache.keys())}")
        
        # Get cached analysis - if not found, trigger it
        if project_id not in _analysis_cache:
            print(f"[PERSONA] Cache miss for {project_id}, attempting real-time analysis")
            
            # Try to run analysis real-time
            import tempfile
            import zipfile
            import httpx
            import os
            
            repo_url = project.get("repository_url", "")
            local_file_path = project.get("local_file_path")
            
            if not repo_url and not local_file_path:
                raise HTTPException(status_code=400, detail="No repository URL or file provided")
            
            # Download and extract the repository as ZIP
            with tempfile.TemporaryDirectory() as temp_dir:
                zip_path = None
                
                # Handle uploaded ZIP files (use local path directly)
                if local_file_path:
                    zip_path = local_file_path
                    if not os.path.exists(zip_path):
                        raise ValueError(f"ZIP file not found: {zip_path}")
                
                # Handle GitHub URLs
                elif "github.com" in repo_url:
                    # Extract owner/repo from URL
                    parts = repo_url.rstrip('/').split('/')
                    owner, repo = parts[-2], parts[-1]
                    archive_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/main.zip"
                    
                    try:
                        response = httpx.get(archive_url, timeout=60, follow_redirects=True)
                        
                        if response.status_code == 404:
                            archive_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/master.zip"
                            response = httpx.get(archive_url, timeout=60, follow_redirects=True)
                        
                        if response.status_code != 200:
                            raise ValueError(f"Failed to download repository (HTTP {response.status_code})")
                        
                        zip_path = os.path.join(temp_dir, "repo.zip")
                        with open(zip_path, 'wb') as f:
                            f.write(response.content)
                    
                    except Exception as download_err:
                        print(f"[PERSONA] Download error: {download_err}")
                        raise
                else:
                    raise ValueError(f"Unsupported repository URL format: {repo_url}")
                
                # Extract and analyze
                try:
                    extract_path = os.path.join(temp_dir, "extracted")
                    with zipfile.ZipFile(zip_path, 'r') as zf:
                        zf.extractall(extract_path)
                    
                    # Find the actual repository directory
                    repo_dir = extract_path
                    subdirs = [d for d in os.listdir(extract_path) if os.path.isdir(os.path.join(extract_path, d))]
                    
                    if len(subdirs) == 1:
                        repo_dir = os.path.join(extract_path, subdirs[0])
                    
                    # Run analyzer
                    from .agents.analyzer import RepositoryAnalyzer
                    analyzer = RepositoryAnalyzer(repo_dir)
                    metadata = analyzer.analyze()
                    chunks = analyzer.code_chunks
                    search_engine = SemanticSearchEngine(chunks)
                    
                    print(f"[PERSONA] Real-time analysis complete, caching results")
                    
                    # Cache the results
                    _analysis_cache[project_id] = (metadata, chunks, search_engine)
                
                except Exception as analyze_err:
                    print(f"[PERSONA] Analysis error: {analyze_err}")
                    import traceback
                    print(traceback.format_exc())
                    raise
        
        metadata, chunks, _ = _analysis_cache[project_id]
        
        # Generate persona-specific analysis
        from .agents.persona_analyzer import PersonaAnalyzer
        
        analyzer = PersonaAnalyzer(metadata, chunks)
        
        if persona == 'sde':
            return analyzer.analyze_for_sde()
        else:
            return analyzer.analyze_for_pm()
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"[PERSONA] Persona analysis error: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Persona analysis failed: {str(e)}")
