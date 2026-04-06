from typing import Dict, Any
from models.schemas import Note
from db.memory_store import MemoryStore
from tools.base_tool import BaseTool

class NotesTool(BaseTool):
    def __init__(self, memory_store: MemoryStore):
        self.memory = memory_store
    
    def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if action == "create_note":
            return self._create_note(params)
        elif action == "search_notes":
            return self._search_notes(params)
        else:
            return {"error": f"Unknown action: {action}"}
    
    def _create_note(self, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            note = Note(
                title=params["title"],
                content=params["content"],
                tags=params.get("tags", [])
            )
            saved_note = self.memory.save_note(note)
            return {
                "success": True,
                "note": saved_note.dict(),
                "message": f"Note '{saved_note.title}' created"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _search_notes(self, params: Dict[str, Any]) -> Dict[str, Any]:
        query = params.get("query", "")
        results = self.memory.search_notes(query)
        return {
            "success": True,
            "notes": [n.dict() for n in results],
            "count": len(results)
        }
    
    def get_actions(self) -> list:
        return ["create_note", "search_notes"]
