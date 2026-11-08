from __future__ import annotations
import asyncio
import json
from datetime import datetime, timezone
from typing import Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.vault import get_jobs, get_job, get_total_costs

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
    
    async def broadcast(self, message: dict):
        disconnected = set()
        for conn in self.active_connections:
            try:
                await conn.send_json(message)
            except Exception:
                disconnected.add(conn)
        self.active_connections -= disconnected

manager = ConnectionManager()

@router.websocket('/ws/pipeline')
async def pipeline_ws(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Send initial state
        jobs = await get_jobs(limit=20)
        job_list = []
        for j in jobs:
            job_list.append({
                'id': j.id,
                'niche': j.niche,
                'status': j.status.value if hasattr(j.status, 'value') else str(j.status),
                'current_stage': j.current_stage,
                'config_json': j.config_json or {},
                'created_at': j.created_at.isoformat() if j.created_at else None,
                'updated_at': j.updated_at.isoformat() if j.updated_at else None,
            })
        await websocket.send_json({'type': 'initial_state', 'jobs': job_list})
        
        # Keep alive and listen for messages
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                msg = json.loads(data)
                # Handle client messages (e.g., approve/reject)
                if msg.get('action') == 'approve':
                    # TODO: implement approval
                    pass
            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_json({'type': 'heartbeat', 'timestamp': datetime.now(timezone.utc).isoformat()})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
