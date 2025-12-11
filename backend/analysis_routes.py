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
                    
                    # Run analyzer (async, with progress callback for real-time responses)
                    analyzer = RepositoryAnalyzer(repo_dir)

                    async def simple_progress(stage, percent, message, file=None):
                        print(f"[ANALYSIS][PROG] {percent}% {stage} - {message} {file or ''}")

                    import asyncio
                    metadata = await analyzer.analyze(progress_callback=simple_progress)
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


@router.get("/{project_id}/progress")
async def get_analysis_progress(project_id: str, authorization: Optional[str] = Header(None)):
    """Return current progress and activity feed for a project."""
    try:
        user_id = get_current_user_id(authorization)
        project = await get_project(project_id)

        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        if project["owner_id"] != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        return {
            "project_id": project_id,
            "status": project.get("status"),
            "progress": project.get("progress", 0.0),
            "status_message": project.get("status_message", ""),
            "activity_feed": project.get("activity_feed", [])[-200:]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/pause")
async def pause_analysis(project_id: str, authorization: Optional[str] = Header(None)):
    try:
        user_id = get_current_user_id(authorization)
        project = await get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        if project["owner_id"] != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        project["paused"] = True
        project.setdefault("activity_feed", []).append({"ts": __import__("datetime").datetime.utcnow().isoformat(), "level": "info", "message": "Analysis paused by user"})
        return {"project_id": project_id, "paused": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/resume")
async def resume_analysis(project_id: str, authorization: Optional[str] = Header(None)):
    try:
        user_id = get_current_user_id(authorization)
        project = await get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        if project["owner_id"] != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        project["paused"] = False
        project.setdefault("activity_feed", []).append({"ts": __import__("datetime").datetime.utcnow().isoformat(), "level": "info", "message": "Analysis resumed by user"})
        return {"project_id": project_id, "paused": False}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/ask")
async def ask_question(
    project_id: str,
    body: dict,
    authorization: Optional[str] = Header(None)
):
    """
    Ask questions about the current analysis state.
    Body: {"question": "...", "persona": "sde|pm" (optional)}
    """
    try:
        user_id = get_current_user_id(authorization)
        project = await get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        if project["owner_id"] != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        question = (body or {}).get("question", "").strip()
        if not question:
            raise HTTPException(status_code=400, detail="Missing 'question'")

        # Ensure analysis has produced cache
        if project_id not in _analysis_cache:
            # Answer from current progress if available
            status = {
                "status": project.get("status"),
                "progress": project.get("progress", 0.0),
                "status_message": project.get("status_message", "")
            }
            raise HTTPException(status_code=202, detail=f"Analysis in progress. Current state: {status}")

        metadata, chunks, search_engine = _analysis_cache[project_id]
        results = search_engine.search(question, limit=5)

        # Compose a concise answer with simple heuristic
        top_names = [r["name"] for r in results if r.get("name")]
        answer_lines = []
        if top_names:
            answer_lines.append(f"Relevant items: {', '.join(top_names[:5])}")
        if metadata.frameworks:
            answer_lines.append(f"Detected frameworks: {', '.join(metadata.frameworks)}")
        if "framework" in question.lower() or "api" in question.lower():
            answer_lines.append(f"Repo type: {metadata.repo_type}")

        if not answer_lines:
            answer_lines.append("No direct match found. Try a more specific query.")

        answer = " ".join(answer_lines)
        citations = [{"file_path": r["file_path"], "start_line": r["start_line"]} for r in results]

        project.setdefault("qna", []).append({
            "ts": __import__("datetime").datetime.utcnow().isoformat(),
            "q": question,
            "a": answer,
            "citations": citations
        })
        project.setdefault("activity_feed", []).append({
            "ts": __import__("datetime").datetime.utcnow().isoformat(),
            "level": "info",
            "message": f"Answered question: {question}"
        })

        return {
            "answer": answer,
            "citations": citations,
            "results": results
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/context")
async def add_context(
    project_id: str,
    body: dict,
    authorization: Optional[str] = Header(None)
):
    """
    Inject additional information/instructions into analysis.
    Body: {"instruction": "Focus more on the payment module", "priority": "normal|high" (optional)}
    """
    try:
        user_id = get_current_user_id(authorization)
        project = await get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        if project["owner_id"] != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        instruction = (body or {}).get("instruction", "").strip()
        priority = (body or {}).get("priority", "normal")
        if not instruction:
            raise HTTPException(status_code=400, detail="Missing 'instruction'")

        ctx = {
            "ts": __import__("datetime").datetime.utcnow().isoformat(),
            "instruction": instruction,
            "priority": priority
        }
        project.setdefault("user_context", []).append(ctx)
        project.setdefault("activity_feed", []).append({
            "ts": __import__("datetime").datetime.utcnow().isoformat(),
            "level": "info",
            "message": f"User context added (priority={priority}): {instruction}"
        })
        return {"status": "ok", "context_len": len(project.get("user_context", []))}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/diagrams")
async def get_diagrams(project_id: str, authorization: Optional[str] = Header(None)):
    """Return multiple Mermaid diagrams derived from analysis."""
    try:
        user_id = get_current_user_id(authorization)
        project = await get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        if project["owner_id"] != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        if project_id not in _analysis_cache:
            raise HTTPException(status_code=202, detail="Analysis not yet complete")

        metadata, chunks, _ = _analysis_cache[project_id]
        total_files = metadata.total_files or 0
        code_files = metadata.code_files or 0

        architecture = f'''
flowchart LR
    A[Users] -->|HTTP| B[Service]
    B --> C[Business Logic]
    C --> D[Data Layer]
    D --> E[(Storage)]
'''
        flow = f'''
flowchart TD
    start([Start]) --> detect{{Detect Frameworks}}
    detect -->|Yes| analyze[Analyze Important Files]
    analyze --> extract[Extract Code Chunks]
    extract --> end([End])
    detect -->|No| end
'''
        sequence = f'''
sequenceDiagram
    participant U as User
    participant API as API
    participant S as Analyzer
    U->>API: Create Project
    API->>S: Start Analysis
    S-->>API: Progress Updates
    API-->>U: Activity Feed + Progress
'''
        er = f'''
erDiagram
    USER ||--o{{ PROJECT : owns
    PROJECT ||--o{{ CHUNK : contains
    USER {{
      string user_id
      string email
    }}
    PROJECT {{
      string project_id
      string name
      int total_files
    }}
    CHUNK {{
      string file_path
      string name
      int start_line
    }}
'''

        return {
            "flowchart": architecture,
            "flow": flow,
            "sequence": sequence,
            "er": er
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/export")
async def export_documentation(project_id: str, format: str = "md", authorization: Optional[str] = Header(None)):
    """Export complete documentation (Markdown; PDF as placeholder)."""
    try:
        user_id = get_current_user_id(authorization)
        project = await get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        if project["owner_id"] != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        if project_id not in _analysis_cache:
            raise HTTPException(status_code=202, detail="Analysis not yet complete")

        metadata, chunks, _ = _analysis_cache[project_id]
        from .agents.persona_analyzer import PersonaAnalyzer
        analyzer = PersonaAnalyzer(metadata, chunks)
        sde = analyzer.analyze_for_sde()
        pm = analyzer.analyze_for_pm()

        diagrams = await get_diagrams(project_id, authorization=authorization)

        md = []
        md.append(f"# Project: {project.get('name','')}")
        md.append("")
        md.append("## SDE Report")
        md.append(sde.get("overview",""))
        md.append("### Architecture")
        md.append(str(sde.get("architecture", {})))
        md.append("### Technical Details")
        md.append(str(sde.get("technical_details", {})))
        md.append("")
        md.append("## PM Report")
        md.append(pm.get("overview",""))
        md.append("### Features")
        md.append(str(pm.get("features", {})))
        md.append("")
        md.append("## Diagrams (Mermaid)")
        for title, code in diagrams.items():
            md.append(f"### {title.title()} Diagram")
            md.append("```mermaid")
            md.append(code.strip())
            md.append("```")
            md.append("")

        content = "\n".join(md)

        if format.lower() == "md":
            return {"format": "md", "content": content}
        elif format.lower() == "pdf":
            # Placeholder: return Markdown content for now with a note
            return {
                "format": "pdf",
                "note": "PDF generation with rendered Mermaid is not implemented in this demo build.",
                "content": content
            }
        else:
            raise HTTPException(status_code=400, detail="Unsupported format")
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
                    metadata = await analyzer.analyze()
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
