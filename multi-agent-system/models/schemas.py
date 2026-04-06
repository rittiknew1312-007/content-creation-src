from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"

class Task(BaseModel):
    id: str = ""
    title: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = datetime.now()
    due_date: Optional[datetime] = None
    tags: List[str] = []
    dependencies: List[str] = []

class CalendarEvent(BaseModel):
    id: str = ""
    title: str
    start_time: datetime
    end_time: datetime
    description: Optional[str] = None
    attendees: List[str] = []

class Note(BaseModel):
    id: str = ""
    title: str
    content: str
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()
    tags: List[str] = []

class UserContext(BaseModel):
    user_id: str
    preferences: Dict[str, Any] = {}
    current_focus: Optional[str] = None
    last_interaction: datetime = datetime.now()

class ChatRequest(BaseModel):
    message: str
    user_id: str = "default_user"

class ChatResponse(BaseModel):
    response: str
    actions_taken: List[str] = []
    data: Dict[str, Any] = {}
