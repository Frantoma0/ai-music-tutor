from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.tools import router as tools_router
from app.api.ws import router as ws_router


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
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(tools_router)
app.include_router(ws_router)

@app.get("/health")
def health() -> dict:
    return {
        "status": "healthy",
        "service": "amt-backend",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
