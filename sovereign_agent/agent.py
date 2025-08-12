from pathlib import Path
from sovereign_agent.core.cognitive_core import CognitiveCore
from sovereign_agent.core.state import SharedSessionState
from sovereign_agent.core.models import TaskPlan, HandlerStepModel
import importlib
import pkgutil
import sys
from typing import Dict
from sovereign_agent.handlers.base import BaseHandler

def discover_handlers():
    handlers = {}
    # import handlers package
    import sovereign_agent.handlers as handlers_pkg
    for finder, name, ispkg in pkgutil.iter_modules(handlers_pkg.__path__):
        if name.startswith("_"):
            continue
        mod = importlib.import_module(f"sovereign_agent.handlers.{name}")
        # find classes inheriting BaseHandler
        for attr in dir(mod):
            obj = getattr(mod, attr)
            try:
                if isinstance(obj, type) and issubclass(obj, BaseHandler) and obj is not BaseHandler:
                    inst = obj()
                    handlers[inst.name] = inst
            except Exception:
                continue
    return handlers

class SovereignAgent:
    def __init__(self, workspace_path: str):
        self.workspace_path = Path(workspace_path).resolve()
        if not self.workspace_path.exists():
            self.workspace_path.mkdir(parents=True, exist_ok=True)
            print(f"Created workspace at: {self.workspace_path}")

        self.state = SharedSessionState(self.workspace_path)

        # Dynamic handler discovery
        self.handlers = discover_handlers()
        print(f"Registered handlers: {list(self.handlers.keys())}")

        self.cognitive_core = CognitiveCore(list(self.handlers.values()))

    def _execute_plan(self, plan: TaskPlan):
        print(f"\nExecuting Plan: {plan.overall_goal}")
        for i, step in enumerate(plan.steps):
            print(f"\n--- Step {i+1}/{len(plan.steps)}: {step.handler_name} ---")
            print(f"Goal: {step.step_goal}")
            handler = self.handlers.get(step.handler_name)
            if not handler:
                print(f"❌ Handler '{step.handler_name}' not found.")
                continue
            try:
                step.status = "running"
                response = handler.execute(step.step_goal, step.input_args, self.state)
                step.result = response
                step.status = "completed" if response.success else "failed"
                print(f"✅ Status: {step.status}\n{response.content}")
                self.state.add_to_history("system", f"Step '{step.step_goal}' completed with status: {step.status}.")
                # Save flight recorder entry
                self.state.save_flight_record()
                if not response.success:
                    print("Plan execution halted due to a failed step.")
                    break
            except KeyboardInterrupt:
                print("Execution interrupted by user.")
                break
            except Exception as e:
                print(f"❌ Unexpected error in {step.handler_name}: {e}")
                break

    def start_session(self):
        print("\n🚀 Sovereign Agent MVP Activated. Type 'exit' to quit.")
        while True:
            try:
                user_input = input("\n> ")
                if user_input.lower().strip() in ["exit", "quit"]:
                    break
                self.state.add_to_history("user", user_input)
                task_plan = self.cognitive_core.orchestrate(user_input, self.state)
                self.state.current_task_plan = task_plan
                if not task_plan or not task_plan.steps:
                    print("I couldn't devise a plan. Try rephrasing.")
                    continue
                print("\n🤖 I have a plan:")
                print(f"Goal: {task_plan.overall_goal}")
                for i, step in enumerate(task_plan.steps):
                    print(f"  {i+1}. {step.step_goal} (using {step.handler_name})")
                confirmation = input("Proceed? (Y/n): ").lower().strip()
                if confirmation in ["y", "yes", ""]:
                    self._execute_plan(task_plan)
                else:
                    print("Plan aborted by user.")
                    self.state.add_to_history("system", "User aborted the proposed plan.")
            except KeyboardInterrupt:
                print("\nSession terminated by user.")
                break
