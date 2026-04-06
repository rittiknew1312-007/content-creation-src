from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from core.orchestrator import Orchestrator
import os

app = FastAPI(title="Multi-Agent Content Creator", version="1.0.0")
orchestrator = Orchestrator()

class ChatRequest(BaseModel):
    message: str
    user_id: str = "default_user"

@app.post("/chat")
async def chat(request: ChatRequest):
    result = await orchestrator.process_request(user_message=request.message, user_id=request.user_id)
    return result

@app.get("/health")
async def health():
    return {"status": "ok", "agents": list(orchestrator.agents.keys())}

app.mount("/ui", StaticFiles(directory="ui"), name="ui")

@app.get("/")
async def root():
    return FileResponse("ui/index.html")
