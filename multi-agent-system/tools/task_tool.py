from typing import Dict, Any
from models.schemas import Task, TaskStatus
from db.memory_store import MemoryStore
from tools.base_tool import BaseTool

class TaskTool(BaseTool):
    def __init__(self, memory_store: MemoryStore):
        self.memory = memory_store
    
    def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if action == "create_task":
            return self._create_task(params)
        elif action == "get_tasks":
            return self._get_tasks(params)
        elif action == "complete_task":
            return self._complete_task(params)
        else:
            return {"error": f"Unknown action: {action}"}
    
    def _create_task(self, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            task = Task(
                title=params["title"],
                description=params.get("description"),
                tags=params.get("tags", [])
            )
            if params.get("due_date"):
                task.due_date = params["due_date"]
            saved_task = self.memory.save_task(task)
            return {
                "success": True,
                "task": saved_task.dict(),
                "message": f"Task '{saved_task.title}' created"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _get_tasks(self, params: Dict[str, Any]) -> Dict[str, Any]:
        tasks = self.memory.get_all_tasks()
        return {
            "success": True,
            "tasks": [t.dict() for t in tasks],
            "count": len(tasks)
        }
    
    def _complete_task(self, params: Dict[str, Any]) -> Dict[str, Any]:
        task_id = params["task_id"]
        updated_task = self.memory.update_task(task_id, status=TaskStatus.COMPLETED)
        if updated_task:
            return {
                "success": True,
                "task": updated_task.dict(),
                "message": f"Task '{updated_task.title}' completed!"
            }
        return {"success": False, "error": "Task not found"}
    
    def get_actions(self) -> list:
        return ["create_task", "get_tasks", "complete_task"]
