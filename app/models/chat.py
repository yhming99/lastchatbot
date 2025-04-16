from pydantic import BaseModel, Field
from typing import Optional

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None # n8n 워크플로우의 sessionKey 와 유사하게 추가

class ChatResponse(BaseModel):
    reply: str 