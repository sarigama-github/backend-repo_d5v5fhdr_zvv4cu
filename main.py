import os
from typing import List, Literal, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from bson import ObjectId

from database import db, create_document, get_documents

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------- Utility helpers ----------
class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if isinstance(v, ObjectId):
            return v
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)


def oid_str(oid) -> str:
    return str(oid) if isinstance(oid, ObjectId) else oid


# --------- Models for requests ---------
class CreateChatRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=120)

class ChatResponse(BaseModel):
    id: str
    title: str

class CreateMessageRequest(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1)

class MessageResponse(BaseModel):
    id: str
    chat_id: str
    role: Literal["user", "assistant"]
    content: str


# ---------- Basic routes -------------
@app.get("/")
def read_root():
    return {"message": "Chat Backend Ready"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"

            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


# --------- Chat Endpoints (DB-backed) ---------
@app.post("/api/chats", response_model=ChatResponse)
def create_chat(req: CreateChatRequest):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    doc = {"title": req.title}
    chat_id = create_document("chat", doc)
    return {"id": chat_id, "title": req.title}


@app.get("/api/chats", response_model=List[ChatResponse])
def list_chats():
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    docs = get_documents("chat", {}, 100)
    return [{"id": oid_str(d.get("_id")), "title": d.get("title", "Untitled")} for d in docs]


@app.get("/api/chats/{chat_id}/messages", response_model=List[MessageResponse])
def list_messages(chat_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    try:
        oid = ObjectId(chat_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid chat id")
    docs = db["message"].find({"chat_id": chat_id}).sort("created_at", 1)
    return [
        {
            "id": oid_str(d.get("_id")),
            "chat_id": d.get("chat_id"),
            "role": d.get("role"),
            "content": d.get("content"),
        }
        for d in docs
    ]


@app.post("/api/chats/{chat_id}/messages", response_model=MessageResponse)
def add_message(chat_id: str, req: CreateMessageRequest):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    try:
        _ = ObjectId(chat_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid chat id")

    if req.role not in ("user", "assistant"):
        raise HTTPException(status_code=400, detail="Invalid role")

    doc = {"chat_id": chat_id, "role": req.role, "content": req.content}
    msg_id = create_document("message", doc)
    return {"id": msg_id, "chat_id": chat_id, "role": req.role, "content": req.content}


# Simple echo assistant to simulate AI response
@app.post("/api/chats/{chat_id}/completion", response_model=MessageResponse)
def completion(chat_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    # Find last user message
    last_user = db["message"].find({"chat_id": chat_id, "role": "user"}).sort("created_at", -1).limit(1)
    last_text = None
    for m in last_user:
        last_text = m.get("content")
    if not last_text:
        raise HTTPException(status_code=400, detail="No user message found")

    reply = f"Assistant: J'ai bien reçu — {last_text}"
    # store assistant message
    msg_id = create_document("message", {"chat_id": chat_id, "role": "assistant", "content": reply})
    return {"id": msg_id, "chat_id": chat_id, "role": "assistant", "content": reply}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
