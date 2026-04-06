from typing import Dict, Any
from agents.base_agent import BaseAgent
from tools.calendar_tool import CalendarTool
from db.memory_store import MemoryStore

class SchedulerAgent(BaseAgent):
    def __init__(self, memory_store: MemoryStore):
        super().__init__("SchedulerAgent", memory_store)
        self.calendar_tool = CalendarTool(memory_store)
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        action = input_data.get("action", "get_events")
        params = input_data.get("params", {})
        
        # Map 'schedule' action to 'create_event'
        if action == "schedule":
            action = "create_event"
            # Extract event info from message
            message = params.get("message", "")
            if "schedule" in message.lower():
                # Simple extraction for meeting titles
                if "meeting" in message.lower():
                    params["title"] = "Team Meeting"
                else:
                    params["title"] = "Scheduled Event"
                # Set default times
                from datetime import datetime, timedelta
                params["start_time"] = (datetime.now() + timedelta(days=1)).isoformat()
                params["end_time"] = (datetime.now() + timedelta(days=1, hours=1)).isoformat()
        
        result = self.calendar_tool.execute(action, params)
        return {
            "agent": self.name,
            "action": action,
            "result": result
        }
    
    def can_handle(self, task_type: str) -> bool:
        return any(t in task_type.lower() for t in ["schedule", "calendar"])
