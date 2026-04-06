from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid
from models.schemas import Task, CalendarEvent, Note, UserContext

class MemoryStore:
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.events: Dict[str, CalendarEvent] = {}
        self.notes: Dict[str, Note] = {}
        self.contexts: Dict[str, UserContext] = {}
        
    def save_task(self, task: Task) -> Task:
        if not task.id:
            task.id = str(uuid.uuid4())
        self.tasks[task.id] = task
        return task
    
    def get_task(self, task_id: str) -> Optional[Task]:
        return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> List[Task]:
        return list(self.tasks.values())
    
    def update_task(self, task_id: str, **updates) -> Optional[Task]:
        if task_id not in self.tasks:
            return None
        task = self.tasks[task_id]
        for key, value in updates.items():
            if hasattr(task, key):
                setattr(task, key, value)
        return task
    
    def delete_task(self, task_id: str) -> bool:
        if task_id in self.tasks:
            del self.tasks[task_id]
            return True
        return False
    
    def save_event(self, event: CalendarEvent) -> CalendarEvent:
        if not event.id:
            event.id = str(uuid.uuid4())
        self.events[event.id] = event
        return event
    
    def get_events(self, start_date: Optional[datetime] = None, 
                   end_date: Optional[datetime] = None) -> List[CalendarEvent]:
        events = list(self.events.values())
        if start_date:
            events = [e for e in events if e.start_time >= start_date]
        if end_date:
            events = [e for e in events if e.end_time <= end_date]
        return events
    
    def save_note(self, note: Note) -> Note:
        if not note.id:
            note.id = str(uuid.uuid4())
        note.updated_at = datetime.now()
        self.notes[note.id] = note
        return note
    
    def get_note(self, note_id: str) -> Optional[Note]:
        return self.notes.get(note_id)
    
    def get_all_notes(self) -> List[Note]:
        return list(self.notes.values())
    
    def search_notes(self, query: str) -> List[Note]:
        results = []
        for note in self.notes.values():
            if query.lower() in note.title.lower() or query.lower() in note.content.lower():
                results.append(note)
        return results
    
    def get_context(self, user_id: str) -> UserContext:
        if user_id not in self.contexts:
            self.contexts[user_id] = UserContext(user_id=user_id)
        return self.contexts[user_id]
    
    def update_context(self, user_id: str, **updates) -> UserContext:
        context = self.get_context(user_id)
        for key, value in updates.items():
            if hasattr(context, key):
                setattr(context, key, value)
        context.last_interaction = datetime.now()
        return context
