import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from sovereign_agent.core.models import TaskPlan

class DynamicWorkspaceContext:
    def __init__(self, workspace_path: Path):
        self.path = Path(workspace_path)
        self.file_tree = {}
        self.analyze()

    def analyze(self):
        files = []
        try:
            for p in self.path.rglob('*'):
                if p.is_file():
                    files.append(str(p.relative_to(self.path)))
        except Exception:
            pass
        self.file_tree = {'files': files}

    def to_json(self):
        return {'path': str(self.path), 'file_tree_summary': self.file_tree}

class SharedSessionState:
    def __init__(self, workspace_path: Path):
        self.workspace_context = DynamicWorkspaceContext(workspace_path)
        self.conversation_history: List[Dict[str, str]] = []
        self.current_task_plan: Optional[TaskPlan] = None
        self.artifacts: Dict[str, Any] = {}
        # flight recorder file
        self.flight_path = Path(workspace_path) / '.sovereign_flight.json'
        self._flight = {'records': []}
        self.save_flight_record()  # initialize

    def add_to_history(self, role: str, content: str):
        self.conversation_history.append({'role': role, 'content': content})

    def update_artifact(self, key: str, value: Any):
        self.artifacts[key] = value

    def save_flight_record(self):
        # append current snapshot
        snapshot = {
            'conversation': list(self.conversation_history),
            'artifacts': dict(self.artifacts),
        }
        self._flight['records'].append(snapshot)
        try:
            self.flight_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.flight_path, 'w') as f:
                json.dump(self._flight, f, indent=2)
        except Exception:
            pass
