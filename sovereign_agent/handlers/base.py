from abc import ABC, abstractmethod
from sovereign_agent.core.models import AgentResponse
from sovereign_agent.core.state import SharedSessionState

class BaseHandler(ABC):
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    def execute(self, step_goal: str, args: dict, state: SharedSessionState) -> AgentResponse:
        pass

    def get_capabilities(self) -> dict:
        return {'name': self.name, 'description': self.description}
