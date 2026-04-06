from typing import Dict, Any, List
from db.memory_store import MemoryStore
from agents.planner_agent import PlannerAgent
from agents.task_agent import TaskAgent
from agents.scheduler_agent import SchedulerAgent
from agents.memory_agent import MemoryAgent

class Orchestrator:
    def __init__(self):
        self.memory = MemoryStore()
        self.agents = {
            "PlannerAgent": PlannerAgent(self.memory),
            "TaskAgent": TaskAgent(self.memory),
            "SchedulerAgent": SchedulerAgent(self.memory),
            "MemoryAgent": MemoryAgent(self.memory)
        }
    
    async def process_request(self, user_message: str, user_id: str = "default_user") -> Dict[str, Any]:
        context = self.memory.get_context(user_id)
        plan_result = self.agents["PlannerAgent"].process({
            "message": user_message,
            "context": context
        })
        
        execution_results = []
        for step in plan_result["plan"]:
            agent_name = step["agent"]
            if agent_name in self.agents:
                result = self.agents[agent_name].process({
                    "action": step.get("action"),
                    "params": {
                        "user_id": user_id,
                        "message": user_message,
                        **step
                    }
                })
                execution_results.append(result)
        
        response = self._generate_response(execution_results)
        self.memory.update_context(user_id, last_query=user_message)
        
        return {
            "response": response,
            "execution_results": execution_results,
            "plan": plan_result["plan"],
            "user_id": user_id
        }
    
    def _generate_response(self, results: List[Dict]) -> str:
        if not results:
            return "I couldn't process your request."
        
        response_parts = []
        for result in results:
            result_data = result.get("result", {})
            if result_data.get("success"):
                if "task" in result_data:
                    response_parts.append(f"✓ {result_data.get('message')}")
                elif "event" in result_data:
                    response_parts.append(f"✓ {result_data.get('message')}")
                elif "note" in result_data:
                    response_parts.append(f"✓ {result_data.get('message')}")
                else:
                    response_parts.append("✓ Action completed")
            else:
                response_parts.append(f"⚠ {result_data.get('error', 'Action failed')}")
        
        return "\n".join(response_parts) if response_parts else "Request processed."
