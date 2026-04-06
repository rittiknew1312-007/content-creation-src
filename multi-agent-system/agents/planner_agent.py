from typing import Dict, Any, List
from agents.base_agent import BaseAgent
from db.memory_store import MemoryStore

class PlannerAgent(BaseAgent):
    def __init__(self, memory_store: MemoryStore):
        super().__init__("Planner", memory_store)
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        user_message = input_data.get("message", "")
        plan = self._create_plan(user_message)
        return {
            "agent": self.name,
            "plan": plan,
            "steps": len(plan)
        }
    
    def _create_plan(self, message: str) -> List[Dict[str, Any]]:
        plan = []
        if any(k in message.lower() for k in ["task", "todo", "work"]):
            plan.append({
                "step": 1,
                "agent": "TaskAgent",
                "action": "create_task",
                "description": "Create or manage tasks"
            })
        if any(k in message.lower() for k in ["schedule", "meeting", "calendar"]):
            plan.append({
                "step": 2,
                "agent": "SchedulerAgent",
                "action": "schedule",
                "description": "Manage calendar"
            })
        if any(k in message.lower() for k in ["note", "remember", "info"]):
            plan.append({
                "step": 3,
                "agent": "MemoryAgent",
                "action": "store_info",
                "description": "Store information"
            })
        if not plan:
            plan.append({
                "step": 1,
                "agent": "MemoryAgent",
                "action": "analyze",
                "description": "Analyze query"
            })
        return plan
    
    def can_handle(self, task_type: str) -> bool:
        return task_type in ["plan", "organize"]
