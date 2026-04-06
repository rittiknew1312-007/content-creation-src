from typing import Dict, Any
from agents.base_agent import BaseAgent
from tools.task_tool import TaskTool
from db.memory_store import MemoryStore

class TaskAgent(BaseAgent):
    def __init__(self, memory_store: MemoryStore):
        super().__init__("TaskAgent", memory_store)
        self.task_tool = TaskTool(memory_store)
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        action = input_data.get("action", "get_tasks")
        params = input_data.get("params", {})
        result = self.task_tool.execute(action, params)
        return {
            "agent": self.name,
            "action": action,
            "result": result
        }
    
    def can_handle(self, task_type: str) -> bool:
        return "task" in task_type.lower()
