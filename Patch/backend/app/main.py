from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.tools import router as tools_router
from app.api.lessons import router as lessons_router
from app.api.uploads import router as uploads_router
from app.api.ws import router as ws_router
from app.db.database import DEFAULT_DB_PATH, initialize_database
from app.api.pipeline_runs import router as pipeline_runs_router
from app.api.progress import router as progress_router
from app.api.coach import router as coach_router
from app.mcp_tools.coach_tool import PracticeCoachTool
from app.mcp_tools.registry import registry as tool_registry
from app.db.progress import init_progress_schema


app = FastAPI(
    title="AI Music Tutor API",
    version="0.1.0",
    description="Local-first backend for MCP-orchestrated piano transcription correction.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(tools_router)
app.include_router(lessons_router)
app.include_router(uploads_router)
app.include_router(ws_router)
app.include_router(pipeline_runs_router)
app.include_router(progress_router)
app.include_router(coach_router)

try:
    tool_registry.register(PracticeCoachTool())
except ValueError:
    pass  # already registered (module reload)

@app.on_event("startup")
async def initialize_app_database() -> None:
    await initialize_database(DEFAULT_DB_PATH)
    await init_progress_schema(DEFAULT_DB_PATH)

@app.get("/health")
def health() -> dict:
    return {
        "status": "healthy",
        "service": "amt-backend",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
