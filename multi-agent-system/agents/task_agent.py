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
        
        # Extract message content for task creation
        if action == "create_task" and "message" in params:
            # Parse natural language to extract task title
            message = params.get("message", "")
            # Simple extraction - look for "create a task to..." pattern
            if "create a task to" in message.lower():
                title = message.lower().split("create a task to")[-1].strip()
            elif "create task" in message.lower():
                title = message.lower().split("create task")[-1].strip()
            else:
                title = message[:50]  # First 50 chars as title
            
            params["title"] = title
            
        result = self.task_tool.execute(action, params)
        return {
            "agent": self.name,
            "action": action,
            "result": result
        }
    
    def can_handle(self, task_type: str) -> bool:
        return "task" in task_type.lower()
