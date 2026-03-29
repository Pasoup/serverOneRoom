from persistent import Persistent


class User(Persistent):
    def __init__(self,gmail,name,id,pno, memOf=list([])):
        self.gmail = gmail
        self.name = name
        self.id = id
        self.phone = pno
        self.rooms : list = memOf

    def getRooms(self):
        return self.rooms

    def to_dict(self):
        return {
            "gmail": self.gmail, 
            "name": self.name,
            "id": self.id,
            "phone": self.phone,
            "rooms": self.rooms
        }
    def createRoom(self):
        pass

    def getGmail(self):
        return self.gmail

    def getID(self):
        return self.id

    def getName(self):
        return self.name

    def getPhoneNo(self):
        return self.phone

    def joinRoom(self):
        pass

    def login(self):
        pass

    def register(self):
        pass

    def setName(self,name):
        self.name = name

    def setPhoneNumber(self,pno):
        self.phone = pno

class Member(User): 
    def __init__(self, gmail, name, id, pno, memOf=list([])):
        User.__init__(self,gmail, name, id, pno, memOf)
        self.currRoom = None

    def openRoom(self,roomID):
        if roomID in self.room:
            idx = self.room.index(roomID)
            self.currRoom = self.room[idx]

    def editCode(self):
        pass

    def exportCode(self):
        pass

    def importCode(self):
        pass

    def joinCall(self):
        pass

    def leaveCall(self):
        pass

    def leaveRoom(self, RID : int):
        self.room.remove(RID)

    def sendText(self,text):
        if self.currRoom:
            self.currRoom.textSent(text,self)

    def startCall(self):
        pass

class Admin(Member):
    def __init__(self, gmail, name, id, pno, roomOwn = None, memOf=[]):
        Member.__init__(self,gmail,name,id,pno,memOf)
        self.roomOwn = roomOwn

    def assignRoom(self, roomOwn):
        self.roomOwn = roomOwn

    def deleteRoom(self):
        del self.roomOwn