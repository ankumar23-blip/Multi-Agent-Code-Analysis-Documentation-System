import os
import asyncio
from fastapi import FastAPI
from .api import router as api_router
from .auth_routes import router as auth_router
from .project_routes import router as project_router
from .analysis_routes import router as analysis_router
from .admin_routes import router as admin_router
from .workers.orchestrator import Orchestrator
from .core import init_db

app = FastAPI(title='MultiAgent Code Analysis API')

# Include routers
app.include_router(auth_router)
app.include_router(project_router)
app.include_router(analysis_router)
app.include_router(admin_router)
app.include_router(api_router, prefix='/api')

@app.on_event('startup')
async def startup():
    await init_db()
    # create orchestrator instance and attach to app
    app.state.orchestrator = Orchestrator(app)
    await app.state.orchestrator.startup()

@app.on_event('shutdown')
async def shutdown():
    await app.state.orchestrator.shutdown()
