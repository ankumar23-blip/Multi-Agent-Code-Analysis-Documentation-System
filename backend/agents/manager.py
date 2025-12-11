import asyncio
from . import ingest, metadata, summarizer, docgen, observability
job_controls = {}

agents = {
    'ingest': ingest,
    'metadata': metadata,
    'summarizer': summarizer,
    'docgen': docgen,
    'observability': observability
}

async def run_agent(name, job_id, payload):
    module = agents.get(name)
    if not module:
        raise RuntimeError(f'Unknown agent: {name}')
    # check pause flag
    await _wait_if_paused(job_id)
    return await module.run(job_id, payload)

async def get_mermaid(job_id):
    # Ask docgen agent to return mermaid
    return await docgen.get_mermaid(job_id)

async def pause_job(job_id):
    job_controls[job_id] = {'paused': True}

async def resume_job(job_id):
    job_controls[job_id] = {'paused': False}

async def _wait_if_paused(job_id):
    import time
    while job_controls.get(job_id, {}).get('paused', False):
        await asyncio.sleep(0.5)
        # continue waiting until resumed
