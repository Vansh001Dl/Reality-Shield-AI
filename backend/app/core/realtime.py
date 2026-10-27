import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.connections = set()

    async def connect(self, websocket):
        await websocket.accept()
        self.connections.add(websocket)

    def disconnect(self, websocket):
        self.connections.discard(websocket)

    async def broadcast(self, event):
        stale = []
        for connection in tuple(self.connections):
            try:
                await connection.send_json(event)
            except Exception:
                stale.append(connection)
        for connection in stale:
            self.disconnect(connection)


manager = ConnectionManager()
_event_loop = None


async def publish_event(event):
    await manager.broadcast(event)


def publish_event_from_worker(event):
    """Schedule an event from a worker thread onto the WebSocket event loop."""
    if _event_loop and _event_loop.is_running():
        asyncio.run_coroutine_threadsafe(publish_event(event), _event_loop)


@router.websocket("/api/v1/ws/alerts")
async def alerts_socket(websocket: WebSocket):
    global _event_loop
    _event_loop = asyncio.get_running_loop()
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
