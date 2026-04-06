from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
from models.schemas import ChatRequest, ChatResponse, Task, CalendarEvent, Note
from core.orchestrator import Orchestrator

orchestrator = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global orchestrator
    orchestrator = Orchestrator()
    print("Multi-Agent System initialized on Cloud Shell!")
    yield
    print("Shutting down...")

app = FastAPI(title="Multi-Agent AI System", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "service": "Multi-Agent AI System",
        "version": "1.0.0",
        "agents": ["Planner", "Task", "Scheduler", "Memory"],
        "status": "running on Cloud Shell"
    }

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        result = await orchestrator.process_request(
            user_message=request.message,
            user_id=request.user_id
        )
        return ChatResponse(
            response=result["response"],
            actions_taken=[str(r) for r in result["execution_results"]],
            data={
                "plan": result["plan"],
                "user_id": result["user_id"]
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tasks")
async def get_tasks():
    tasks = orchestrator.memory.get_all_tasks()
    return {"tasks": [t.dict() for t in tasks], "count": len(tasks)}

@app.post("/tasks")
async def create_task(task: Task):
    saved_task = orchestrator.memory.save_task(task)
    return {"task": saved_task.dict(), "message": "Task created"}

@app.get("/schedule")
async def get_schedule():
    events = orchestrator.memory.get_events()
    return {"events": [e.dict() for e in events], "count": len(events)}

@app.post("/schedule")
async def create_event(event: CalendarEvent):
    saved_event = orchestrator.memory.save_event(event)
    return {"event": saved_event.dict(), "message": "Event created"}

@app.get("/notes")
async def get_notes():
    notes = orchestrator.memory.get_all_notes()
    return {"notes": [n.dict() for n in notes], "count": len(notes)}

@app.post("/notes")
async def create_note(note: Note):
    saved_note = orchestrator.memory.save_note(note)
    return {"note": saved_note.dict(), "message": "Note created"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
