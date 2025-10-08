from typing import Dict
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        # Словарь для хранения активных соединений: {task_id: websocket_object}
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, task_id: str):
        await websocket.accept()
        self.active_connections[task_id] = websocket

    def disconnect(self, task_id: str):
        if task_id in self.active_connections:
            del self.active_connections[task_id]

    async def send_progress(self, task_id: str, message: dict):
        if task_id in self.active_connections:
            websocket = self.active_connections[task_id]
            await websocket.send_json(message)


# Один экземпляр менеджера на все приложение
manager = ConnectionManager()
