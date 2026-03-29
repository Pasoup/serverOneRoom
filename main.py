import os
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import ZODB, ZODB.FileStorage
import transaction
from persistent import Persistent
from classFiles.RoomClass import RoomObj, Chat, Workshop, Admin
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
    admin_username: str

@app.post("/claim_server")
def claim_server(data: RoomCreateRequest):
    creatorAdmin = Admin(name=data.admin_username)
    admin_obj = root.users.get(data.admin_username) 
        
    if not admin_obj:
        raise HTTPException(status_code=404, detail="Admin User not found in DB")

   
    new_room = RoomObj(
        Rname=data.Rname,
        RID=data.RID,
        desc=data.desc,
        color=data.color,
        admin=creatorAdmin, 
        mem=[data.admin_username]
    )

    root.active_room = new_room
    transaction.commit()
    return {"status": "success"}

@app.get("/room_info")
def get_room_info():
    if root.active_room is None:
        return {"status": "available"}
    
    room = root.active_room
    return {
        "status": "active",
        "name": room.getRoomName(),
        "id": room.getRoomID(),
        "admin": room.getAdmin().getName(),
        "description": room.getDescription()
    }



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