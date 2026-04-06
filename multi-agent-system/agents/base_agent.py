from abc import ABC, abstractmethod
from typing import Dict, Any
from db.memory_store import MemoryStore

class BaseAgent(ABC):
    def __init__(self, name: str, memory_store: MemoryStore):
        self.name = name
        self.memory = memory_store
    
    @abstractmethod
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def can_handle(self, task_type: str) -> bool:
        pass
