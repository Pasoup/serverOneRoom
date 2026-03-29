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

class JoinRequest(BaseModel):
    username: str
    roomID: str


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
            "role": "admin" if is_admin else "member",
        }
    
    return {"status": "access_denied"}


@app.get("/room_info/free")
def get_free_info():
    room = root.active_room
    return {
        "status" : "activate",
        "name" : room.getRoomName(),
        "description" : room.description,
        "roomID" : room.getRoomID()
    }

@app.get("/room_members")
def get_room_members():
    if root.active_room is None:
        return {"members": []}
    
    return {"members": root.active_room.member}


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

root_obj = connection.root()



@app.post("/join_room")
async def join_room(data: JoinRequest):
    room = root_obj.get('active_room')
    
    if not room or room.getRoomID() != data.roomID:
        raise HTTPException(status_code=404, detail="Room not found on this server!")

   
    if data.username not in room.member:
        room.member.append(data.username)
        
    
        room._p_changed = True 
        transaction.commit()
    
    return {"status": "success", "message": f"{data.username} joined {room.getRoomName()}"}


@app.get("/get_members")
async def get_members(roomID: str):
    room = root_obj.get('active_room')

    if not room or room.getRoomID() != roomID:
            raise HTTPException(status_code=404, detail="Room not found")
            
    return {"members": room.member}