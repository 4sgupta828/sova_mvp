from pathlib import Path
from sovereign_agent.core.cognitive_core import CognitiveCore
from sovereign_agent.core.state import SharedSessionState
from sovereign_agent.core.models import TaskPlan, HandlerStepModel
import importlib
import pkgutil
import sys
import os
from typing import Dict
from sovereign_agent.handlers.base import BaseHandler

# Import readline for command history and line editing
try:
    import readline
    READLINE_AVAILABLE = True
except ImportError:
    # On Windows, try pyreadline3
    try:
        import pyreadline3 as readline
        READLINE_AVAILABLE = True
    except ImportError:
        READLINE_AVAILABLE = False

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
        
        # Set up readline for command history and line editing
        self._setup_readline()

    def _setup_readline(self):
        """Set up readline for command history and line editing."""
        if not READLINE_AVAILABLE:
            print("Note: Command history not available. Install 'pyreadline3' on Windows for better experience.")
            return
            
        # Set up history file
        self.history_file = os.path.expanduser("~/.sovereign_agent_history")
        
        try:
            # Load existing history
            readline.read_history_file(self.history_file)
        except (FileNotFoundError, PermissionError):
            pass  # No history file yet, that's fine
        
        # Configure history
        readline.set_history_length(100)  # Keep last 100 commands
        
        # Set up basic tab completion for common commands
        readline.set_completer(self._completer)
        readline.parse_and_bind('tab: complete')
        
        # Enable standard readline key bindings
        readline.parse_and_bind('set editing-mode emacs')  # Use emacs-style key bindings
        
    def _completer(self, text, state):
        """Simple tab completion for common commands."""
        common_commands = [
            'list', 'search', 'find', 'run', 'test', 'build', 'compile',
            'show', 'display', 'check', 'analyze', 'create', 'delete',
            'help', 'exit', 'quit'
        ]
        
        matches = [cmd for cmd in common_commands if cmd.startswith(text.lower())]
        
        if state < len(matches):
            return matches[state]
        return None
        
    def _save_history(self):
        """Save command history to file."""
        if READLINE_AVAILABLE:
            try:
                readline.write_history_file(self.history_file)
            except (PermissionError, OSError):
                pass  # Can't save history, but don't crash
    
    def _format_help_text(self, text: str) -> str:
        """Format help text with subtle styling."""
        return f"\033[2m{text}\033[0m"  # Dim text
    

    def _execute_plan(self, plan: TaskPlan):
        print(f"\nExecuting Plan: {plan.overall_goal}")
        
        # Collect context from previous steps
        step_context = {}
        
        for i, step in enumerate(plan.steps):
            print(f"\n--- Step {i+1}/{len(plan.steps)}: {step.handler_name} ---")
            print(f"Goal: {step.step_goal}")
            handler = self.handlers.get(step.handler_name)
            if not handler:
                print(f"❌ Handler '{step.handler_name}' not found.")
                continue
            try:
                step.status = "running"
                
                # Add context from previous steps to input args
                enhanced_args = step.input_args.copy()
                enhanced_args["__step_context"] = step_context
                enhanced_args["__previous_results"] = [
                    {"step_goal": prev_step.step_goal, "result": prev_step.result}
                    for prev_step in plan.steps[:i] if prev_step.result
                ]
                
                response = handler.execute(step.step_goal, enhanced_args, self.state)
                step.result = response
                
                # Store step result in context for next steps
                if response.success:
                    step_context[f"step_{i+1}_result"] = response.content
                    step_context[f"step_{i+1}_artifacts"] = response.artifacts_created
                step.status = "completed" if response.success else "failed"
                print(f"✅ Status: {step.status}\n{response.content}")
                
                # If output was truncated, offer to show full output
                artifacts = getattr(response, 'artifacts_created', {})
                if artifacts and artifacts.get('full_stdout'):
                    full_output = artifacts['full_stdout']
                    if len(full_output.split('\n')) > 50:  # If more than 50 lines
                        print(f"\n{self._format_help_text('💡 Output was truncated. To see full output, ask: \"show me the full output from that last command\"')}")
                
                self.state.add_to_history("system", f"Step '{step.step_goal}' completed with status: {step.status}.")
                # Save flight recorder entry
                self.state.save_flight_record()
                if not response.success:
                    print(f"❌ Step failed. Execution halted.")
                    print(f"{self._format_help_text('💡 You can try rephrasing your request or use a more specific command.')}")
                    self.state.add_to_history("system", f"Step failed: {step.step_goal}. Error: {response.content}")
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
                self._execute_plan(task_plan)
            except KeyboardInterrupt:
                print("\nSession terminated by user.")
                break
        
        # Save command history when session ends
        self._save_history()
