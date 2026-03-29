import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import ZODB, ZODB.FileStorage
import transaction
from persistent import Persistent
from classFiles.RoomClass import RoomObj, Chat, Workshop 

app = FastAPI()

storage = ZODB.FileStorage.FileStorage('database.fs')
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
    
    if data.admin_username not in root.users:
        raise HTTPException(status_code=404, detail="User not found")
    
    admin_user = root.users[data.admin_username]

   
    # We pass the user object as the admin
    new_room = RoomObj(
        Rname=data.name,
        RID=data.roomID,
        desc=data.description,
        color=data.color,
        admin=admin_user 
    )

   
    root.active_room = new_room
    

    transaction.commit()
    
    return {
        "status": "success",
        "message": f"Server is now {new_room.getRoomName()}",
        "admin": new_room.getAdmin().getName()
    }

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