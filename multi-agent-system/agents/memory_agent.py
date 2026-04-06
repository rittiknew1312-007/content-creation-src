from typing import Dict, Any
from agents.base_agent import BaseAgent
from tools.notes_tool import NotesTool
from db.memory_store import MemoryStore

class MemoryAgent(BaseAgent):
    def __init__(self, memory_store: MemoryStore):
        super().__init__("MemoryAgent", memory_store)
        self.notes_tool = NotesTool(memory_store)
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        action = input_data.get("action", "search_notes")
        params = input_data.get("params", {})
        result = self.notes_tool.execute(action, params)
        return {
            "agent": self.name,
            "action": action,
            "result": result
        }
    
    def can_handle(self, task_type: str) -> bool:
        return any(t in task_type.lower() for t in ["memory", "note", "info"])
