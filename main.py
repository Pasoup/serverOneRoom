import os
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import ZODB, ZODB.FileStorage
import transaction
from persistent import Persistent
from classFiles.RoomClass import RoomObj, Chat, Workshop, Admin
from classFiles.UserClass import User
app = FastAPI()

db_path = "/data/room1.fs" if os.path.exists("/data") else "room1.fs"
storage = ZODB.FileStorage.FileStorage(db_path)
db = ZODB.DB(storage)
connection = db.open()
root = connection.root


if not hasattr(root, 'active_room'):
    root.active_room = None  # Server starts unclaimed
    transaction.commit()

class RoomCreateRequest(BaseModel):
    name: str
    description: str
    roomID: str
    color: str
    # Admin Data
    admin_name: str
    admin_gmail: str
    admin_id: str
    admin_pno: str

@app.post("/claim_server")
def claim_server(data: RoomCreateRequest):
    creator_admin = Admin(
            gmail=data.admin_gmail,
            name=data.admin_name,
            id=data.admin_id,
            pno=data.admin_pno
        )
   
    new_room = RoomObj(
        Rname=data.name,
        RID=data.roomID,
        desc=data.description,
        color=data.color,
        admin=creator_admin, 
        mem=[data.admin_name]
    )

    root.active_room = new_room
    transaction.commit()
    return {
        "status": "success", 
        "admin": new_room.getAdmin().getName(),
        "room": new_room.getRoomName()
    }

@app.get("/room_info")
def get_room_info(username: str = None):
    if root.active_room is None:
        return {"status": "available"}
    
    room = root.active_room
    is_admin = (room.getAdmin().getName() == username)
    is_member = (username in room.member)

    if is_admin or is_member:
        return {
            "status": "active",
            "name": room.getRoomName(),
            "description": room.description,
            "roomID": room.getRoomID(),
            "color": room.color,
            "role": "admin" if is_admin else "member"
        }
    
    return {"status": "access_denied"}


# Manages users typing in the workshop
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@app.websocket("/ws/workshop")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Receive typing data from one user
            data = await websocket.receive_text()
            # Send that data to EVERYONE else in the room
            await manager.broadcast(data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)