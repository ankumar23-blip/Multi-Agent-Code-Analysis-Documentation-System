from fastapi import APIRouter, Request, HTTPException
from .schemas import *
from .auth import require_role

router = APIRouter()

@router.post('/start-analysis', response_model=AnalysisStartResponse)
async def start_analysis(payload: AnalysisStartRequest, request: Request):
    """Start a new code analysis job."""
    try:
        orch = request.app.state.orchestrator
        job_id = await orch.start_job(payload.repository_url, payload.options)
        return {"job_id": job_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post('/control/{job_id}/pause')
async def pause_job(job_id: str, request: Request):
    """Pause a running job."""
    try:
        orch = request.app.state.orchestrator
        await orch.pause(job_id)
        return {"status": "paused"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post('/control/{job_id}/resume')
async def resume_job(job_id: str, request: Request):
    """Resume a paused job."""
    try:
        orch = request.app.state.orchestrator
        await orch.resume(job_id)
        return {"status": "resumed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/jobs/{job_id}/status')
async def job_status(job_id: str, request: Request):
    """Get the status of a job."""
    try:
        orch = request.app.state.orchestrator
        status = await orch.status(job_id)
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/docs/{job_id}/mermaid')
async def get_mermaid(job_id: str, request: Request):
    """Get the Mermaid diagram for a completed job."""
    try:
        orch = request.app.state.orchestrator
        mermaid = await orch.get_mermaid(job_id)
        return {"mermaid": mermaid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
