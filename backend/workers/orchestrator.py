import asyncio
import uuid
import json
from ..agents import manager as agent_manager
import redis.asyncio as aioredis
import os

REDIS_URL = os.getenv('REDIS_URL','redis://redis:6379/0')

class Orchestrator:
    def __init__(self, app):
        self.app = app
        self.jobs = {}
        self.redis = None

    async def startup(self):
        self.redis = await aioredis.from_url(REDIS_URL)
        # placeholder for langgraph init
        print('Orchestrator started')

    async def shutdown(self):
        if self.redis:
            await self.redis.close()

    async def start_job(self, repo_url: str, options: dict):
        job_id = str(uuid.uuid4())
        self.jobs[job_id] = {'status':'queued','progress':0.0, 'mermaid':''}
        # schedule the orchestrated pipeline
        asyncio.create_task(self._run_pipeline(job_id, repo_url, options))
        return job_id

    async def _run_pipeline(self, job_id, repo_url, options):
        self.jobs[job_id]['status'] = 'running'
        # Step 1: Preprocess (agent)
        await agent_manager.run_agent('ingest', job_id, {'repo_url':repo_url})
        self.jobs[job_id]['progress'] = 0.25
        await agent_manager.run_agent('metadata', job_id, {})
        self.jobs[job_id]['progress'] = 0.5
        await agent_manager.run_agent('summarizer', job_id, {})
        self.jobs[job_id]['progress'] = 0.8
        await agent_manager.run_agent('docgen', job_id, {})
        self.jobs[job_id]['progress'] = 1.0
        # generate a mermaid flow
        self.jobs[job_id]['mermaid'] = await agent_manager.get_mermaid(job_id)
        self.jobs[job_id]['status'] = 'completed'

    async def pause(self, job_id):
        await agent_manager.pause_job(job_id)
        self.jobs[job_id]['status'] = 'paused'

    async def resume(self, job_id):
        await agent_manager.resume_job(job_id)
        self.jobs[job_id]['status'] = 'running'

    async def status(self, job_id):
        return self.jobs.get(job_id, {'status':'unknown', 'progress':0.0})

    async def get_mermaid(self, job_id):
        return self.jobs.get(job_id, {}).get('mermaid','')
