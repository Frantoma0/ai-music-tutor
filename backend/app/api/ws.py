from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/pipeline/{job_id}")
async def pipeline_progress(websocket: WebSocket, job_id: str) -> None:
    await websocket.accept()
    try:
        await websocket.send_json(
            {
                "job_id": job_id,
                "status": "connected",
                "message": "Pipeline WebSocket stub connected.",
            }
        )

        while True:
            message = await websocket.receive_text()
            await websocket.send_json(
                {
                    "job_id": job_id,
                    "status": "echo",
                    "message": message,
                }
            )
    except WebSocketDisconnect:
        return
