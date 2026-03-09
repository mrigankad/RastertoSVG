"""WebSocket routes for real-time updates."""

import asyncio
import json
import logging
from typing import Dict, Optional, Set
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from starlette.websockets import WebSocketState

from app.services.job_tracker import JobTracker

logger = logging.getLogger(__name__)

router = APIRouter()

# Global connection manager
class ConnectionManager:
    """Manage WebSocket connections."""
    
    def __init__(self):
        # Map of job_id -> set of connected websockets
        self.job_connections: Dict[str, Set[WebSocket]] = {}
        # Map of websocket -> set of job_ids it's subscribed to
        self.connection_jobs: Dict[WebSocket, Set[str]] = {}
        # Map of user_id -> set of websockets (for user-wide notifications)
        self.user_connections: Dict[str, Set[WebSocket]] = {}
        
    async def connect(self, websocket: WebSocket, job_ids: Optional[list] = None, user_id: Optional[str] = None):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        
        self.connection_jobs[websocket] = set()
        
        if job_ids:
            for job_id in job_ids:
                await self.subscribe_to_job(websocket, job_id)
        
        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(websocket)
            
        logger.info(f"WebSocket connected. Jobs: {job_ids}, User: {user_id}")
    
    async def disconnect(self, websocket: WebSocket, user_id: Optional[str] = None):
        """Handle WebSocket disconnection."""
        # Unsubscribe from all jobs
        job_ids = self.connection_jobs.get(websocket, set()).copy()
        for job_id in job_ids:
            await self.unsubscribe_from_job(websocket, job_id)
        
        if websocket in self.connection_jobs:
            del self.connection_jobs[websocket]
        
        # Remove from user connections
        if user_id and user_id in self.user_connections:
            self.user_connections[user_id].discard(websocket)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        
        logger.info("WebSocket disconnected")
    
    async def subscribe_to_job(self, websocket: WebSocket, job_id: str):
        """Subscribe a websocket to job updates."""
        if job_id not in self.job_connections:
            self.job_connections[job_id] = set()
        self.job_connections[job_id].add(websocket)
        self.connection_jobs[websocket].add(job_id)
        
        # Send current status immediately
        job_tracker = JobTracker()
        job_data = job_tracker.get_job(job_id)
        if job_data:
            await self.send_to_websocket(websocket, {
                "type": "job.status",
                "job_id": job_id,
                "data": job_data,
            })
    
    async def unsubscribe_from_job(self, websocket: WebSocket, job_id: str):
        """Unsubscribe a websocket from job updates."""
        if job_id in self.job_connections:
            self.job_connections[job_id].discard(websocket)
            if not self.job_connections[job_id]:
                del self.job_connections[job_id]
        
        if websocket in self.connection_jobs:
            self.connection_jobs[websocket].discard(job_id)
    
    async def send_to_websocket(self, websocket: WebSocket, message: dict):
        """Send a message to a specific websocket."""
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Failed to send message to websocket: {e}")
    
    async def broadcast_to_job(self, job_id: str, message: dict):
        """Broadcast a message to all websockets subscribed to a job."""
        if job_id not in self.job_connections:
            return
        
        disconnected = []
        for websocket in self.job_connections[job_id]:
            try:
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_json(message)
                else:
                    disconnected.append(websocket)
            except Exception as e:
                logger.error(f"Failed to broadcast to websocket: {e}")
                disconnected.append(websocket)
        
        # Clean up disconnected websockets
        for websocket in disconnected:
            await self.unsubscribe_from_job(websocket, job_id)
    
    async def broadcast_to_user(self, user_id: str, message: dict):
        """Broadcast a message to all websockets for a user."""
        if user_id not in self.user_connections:
            return
        
        disconnected = []
        for websocket in self.user_connections[user_id]:
            try:
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_json(message)
                else:
                    disconnected.append(websocket)
            except Exception as e:
                logger.error(f"Failed to broadcast to user websocket: {e}")
                disconnected.append(websocket)
        
        # Clean up disconnected websockets
        for websocket in disconnected:
            self.user_connections[user_id].discard(websocket)
        
        if not self.user_connections[user_id]:
            del self.user_connections[user_id]


# Global connection manager
manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    jobs: Optional[str] = Query(None, description="Comma-separated job IDs to subscribe to"),
    user_id: Optional[str] = Query(None, description="User ID for user-wide notifications"),
):
    """
    WebSocket endpoint for real-time job updates.
    
    Query Parameters:
    - jobs: Comma-separated list of job IDs to subscribe to
    - user_id: User ID for receiving user-wide notifications
    
    Message Types:
    - Client -> Server:
      - {"action": "subscribe", "job_id": "..."}
      - {"action": "unsubscribe", "job_id": "..."}
      - {"action": "ping"}
    
    - Server -> Client:
      - {"type": "job.status", "job_id": "...", "data": {...}}
      - {"type": "job.progress", "job_id": "...", "progress": 0.5, "stage": "..."}
      - {"type": "job.completed", "job_id": "...", "result": {...}}
      - {"type": "job.failed", "job_id": "...", "error": "..."}
      - {"type": "pong"}
    """
    job_ids = jobs.split(",") if jobs else []
    await manager.connect(websocket, job_ids, user_id)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                action = message.get("action")
                
                if action == "subscribe":
                    job_id = message.get("job_id")
                    if job_id:
                        await manager.subscribe_to_job(websocket, job_id)
                        await manager.send_to_websocket(websocket, {
                            "type": "subscription.confirmed",
                            "job_id": job_id,
                        })
                
                elif action == "unsubscribe":
                    job_id = message.get("job_id")
                    if job_id:
                        await manager.unsubscribe_from_job(websocket, job_id)
                
                elif action == "ping":
                    await manager.send_to_websocket(websocket, {
                        "type": "pong",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                
                elif action == "get_status":
                    job_id = message.get("job_id")
                    if job_id:
                        job_tracker = JobTracker()
                        job_data = job_tracker.get_job(job_id)
                        await manager.send_to_websocket(websocket, {
                            "type": "job.status",
                            "job_id": job_id,
                            "data": job_data,
                        })
                
                else:
                    await manager.send_to_websocket(websocket, {
                        "type": "error",
                        "message": f"Unknown action: {action}",
                    })
            
            except json.JSONDecodeError:
                await manager.send_to_websocket(websocket, {
                    "type": "error",
                    "message": "Invalid JSON",
                })
    
    except WebSocketDisconnect:
        await manager.disconnect(websocket, user_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await manager.disconnect(websocket, user_id)


# Functions to be called from other parts of the application
async def notify_job_update(job_id: str, data: dict):
    """Notify all connected clients about a job update."""
    await manager.broadcast_to_job(job_id, {
        "type": "job.status",
        "job_id": job_id,
        "data": data,
    })


async def notify_job_progress(job_id: str, progress: float, stage: str):
    """Notify about job progress."""
    await manager.broadcast_to_job(job_id, {
        "type": "job.progress",
        "job_id": job_id,
        "progress": progress,
        "stage": stage,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


async def notify_job_completed(job_id: str, result: dict):
    """Notify that a job is completed."""
    await manager.broadcast_to_job(job_id, {
        "type": "job.completed",
        "job_id": job_id,
        "result": result,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


async def notify_job_failed(job_id: str, error: str):
    """Notify that a job has failed."""
    await manager.broadcast_to_job(job_id, {
        "type": "job.failed",
        "job_id": job_id,
        "error": error,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


async def notify_user(user_id: str, notification: dict):
    """Send a notification to all connections for a user."""
    await manager.broadcast_to_user(user_id, {
        "type": "notification",
        "data": notification,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
