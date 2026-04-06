from typing import Dict, Any
from datetime import datetime
from models.schemas import CalendarEvent
from db.memory_store import MemoryStore
from tools.base_tool import BaseTool

class CalendarTool(BaseTool):
    def __init__(self, memory_store: MemoryStore):
        self.memory = memory_store
    
    def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if action == "create_event":
            return self._create_event(params)
        elif action == "get_events":
            return self._get_events(params)
        else:
            return {"error": f"Unknown action: {action}"}
    
    def _create_event(self, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            event = CalendarEvent(
                title=params["title"],
                start_time=datetime.fromisoformat(params["start_time"]),
                end_time=datetime.fromisoformat(params["end_time"]),
                description=params.get("description"),
                attendees=params.get("attendees", [])
            )
            saved_event = self.memory.save_event(event)
            return {
                "success": True,
                "event": saved_event.dict(),
                "message": f"Event '{saved_event.title}' created"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _get_events(self, params: Dict[str, Any]) -> Dict[str, Any]:
        start = params.get("start_date")
        end = params.get("end_date")
        if start:
            start = datetime.fromisoformat(start)
        if end:
            end = datetime.fromisoformat(end)
        events = self.memory.get_events(start, end)
        return {
            "success": True,
            "events": [e.dict() for e in events],
            "count": len(events)
        }
    
    def get_actions(self) -> list:
        return ["create_event", "get_events"]
