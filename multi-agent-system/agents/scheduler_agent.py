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
        result = self.calendar_tool.execute(action, params)
        return {
            "agent": self.name,
            "action": action,
            "result": result
        }
    
    def can_handle(self, task_type: str) -> bool:
        return any(t in task_type.lower() for t in ["schedule", "calendar"])
