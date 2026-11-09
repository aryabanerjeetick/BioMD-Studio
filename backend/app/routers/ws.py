"""
WebSocket handler for real-time job status updates.
"""

import asyncio
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ..services.job_manager import register_status_callback, unregister_status_callback

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/jobs/{job_id}")
async def job_status_websocket(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint for real-time job status updates.
    Sends JSON messages with job progress.
    """
    await websocket.accept()
    logger.info(f"WebSocket connected for job {job_id}")

    queue: asyncio.Queue = asyncio.Queue()

    async def on_status_update(update: dict):
        await queue.put(update)

    register_status_callback(job_id, on_status_update)

    try:
        while True:
            try:
                # Wait for status updates with timeout
                update = await asyncio.wait_for(queue.get(), timeout=30.0)
                await websocket.send_json(update)

                # If job is terminal, close connection
                if update.get("status") in ("completed", "completed_with_warnings",
                                              "failed", "cancelled"):
                    await websocket.close()
                    break
            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_json({
                    "type": "heartbeat",
                    "job_id": job_id,
                })
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for job {job_id}")
    except Exception as e:
        logger.error(f"WebSocket error for job {job_id}: {e}")
    finally:
        unregister_status_callback(job_id, on_status_update)
