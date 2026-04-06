from typing import Dict, Any
from datetime import datetime, timedelta
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
            return {"success": False, "error": f"Unknown action: {action}"}
    
    def _create_event(self, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Validate required fields
            if "title" not in params:
                return {"success": False, "error": "Event title is required"}
            
            # Set default times if not provided
            start_time = params.get("start_time")
            end_time = params.get("end_time")
            
            if not start_time:
                start_time = (datetime.now() + timedelta(days=1)).isoformat()
            if not end_time:
                end_time = (datetime.now() + timedelta(days=1, hours=1)).isoformat()
            
            event = CalendarEvent(
                title=params["title"],
                start_time=datetime.fromisoformat(start_time) if isinstance(start_time, str) else start_time,
                end_time=datetime.fromisoformat(end_time) if isinstance(end_time, str) else end_time,
                description=params.get("description", ""),
                attendees=params.get("attendees", [])
            )
            saved_event = self.memory.save_event(event)
            return {
                "success": True,
                "event": saved_event.model_dump(),
                "message": f"✅ Event '{saved_event.title}' scheduled for {saved_event.start_time.strftime('%Y-%m-%d %H:%M')}"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _get_events(self, params: Dict[str, Any]) -> Dict[str, Any]:
        start = params.get("start_date")
        end = params.get("end_date")
        if start:
            start = datetime.fromisoformat(start) if isinstance(start, str) else start
        if end:
            end = datetime.fromisoformat(end) if isinstance(end, str) else end
        events = self.memory.get_events(start, end)
        return {
            "success": True,
            "events": [e.model_dump() for e in events],
            "count": len(events)
        }
    
    def get_actions(self) -> list:
        return ["create_event", "get_events"]
