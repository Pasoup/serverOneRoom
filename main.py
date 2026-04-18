import os
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import ZODB, ZODB.FileStorage
import transaction
from persistent import Persistent
from classFiles.RoomClass import RoomObj, Chat, Workshop, Admin
from classFiles.UserClass import User
from datetime import timedelta

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

class ChatMessage(BaseModel):
    username: str
    text: str
    roomID: str

class AdminActionRequest(BaseModel):
    roomID: str
    admin: str
    target: str

@app.post("/send_chat")
async def send_chat(msg: ChatMessage):
    room = root_obj.get('active_room')
    
    if not room or room.getRoomID() != msg.roomID:
        raise HTTPException(status_code=404, detail="Room not found")

    
    room.chat.addConversation(msg.text, msg.username)
    
    
    room.chat._p_changed = True
    transaction.commit()
    
    return {"status": "success"}

@app.get("/get_chat")
async def get_chat(roomID: str):
    room = root_obj.get('active_room')
    
    if not room or room.getRoomID() != roomID:
        return []

    history = room.chat.getChatHistory()
    

    output = []
    for c in history:
        timeObj, sender, content = c.getDetail()

        localTime = timeObj + timedelta(hours=7)

        output.append({
            "time": localTime.strftime("%H:%M"),
            "sender": sender,
            "content": content
        })
        
    return output

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
    new_room.chat = Chat()
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
            "admin_name": room.getAdmin().getName(),
            "role": "admin" if is_admin else "member",
        }
    
    return {"status": "access_denied"}


@app.get("/room_info/free")
def get_free_info():
    room = root.active_room
    
    # Safety check: if there is no active room at all
    if room is None:
        return {"status": "no_room", "member_count": 0}

    # Count the members in the list
    member_count = len(room.member)
    
    return {
        "status" : "activate",
        "name" : room.getRoomName(),
        "description" : room.description,
        "roomID" : room.getRoomID(),
        "member_count": member_count,
        "has_members": member_count > 0
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


@app.post("/leave_room")
async def leave_room(data: JoinRequest): 
    room = root_obj.get('active_room')
    
    if not room or room.getRoomID() != data.roomID:
        raise HTTPException(status_code=404, detail="Room not found")

    if data.username in room.member:
        room.member.remove(data.username)
        
       
        room._p_changed = True 
        transaction.commit()
        return {"status": "success", "message": f"{data.username} left the room"}
    
    return {"status": "error", "message": "User was not in the room"}

@app.post("/kick_member")
async def kick_member(data: AdminActionRequest):
    room = root_obj.get('active_room')
    
    if not room or room.getRoomID() != data.roomID:
        raise HTTPException(status_code=404, detail="Room not found")

    if room.getAdmin().getName() != data.admin:
        raise HTTPException(status_code=403, detail="Access denied: Only the admin can kick members")

    if data.target in room.member:
        room.member.remove(data.target)
        
        room._p_changed = True 
        transaction.commit()
        return {"status": "success", "message": f"{data.target} was kicked from the room"}
    
    return {"status": "error", "message": "Target user was not found in the room"}


@app.post("/transfer_host")
async def transfer_host(data: AdminActionRequest):
    room = root_obj.get('active_room')
    
    if not room or room.getRoomID() != data.roomID:
        raise HTTPException(status_code=404, detail="Room not found")

    if room.getAdmin().getName() != data.admin:
        raise HTTPException(status_code=403, detail="Access denied: Only the admin can transfer host")

    if data.target not in room.member:
        raise HTTPException(status_code=404, detail="Target user must be in the room to become host")
        
    room.admin.name = data.target
    
    room.admin._p_changed = True
    room._p_changed = True
    transaction.commit()
    
    return {"status": "success", "message": f"Host successfully transferred to {data.target}"}
