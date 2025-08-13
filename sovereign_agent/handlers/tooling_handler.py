import shutil
import tempfile
import subprocess
import os
import re
from sovereign_agent.handlers.base import BaseHandler
from sovereign_agent.core.models import AgentResponse
from sovereign_agent.core.state import SharedSessionState
from sovereign_agent.utils.output_formatter import OutputFormatter
from pathlib import Path

# simple dangerous command pattern matcher
DANGEROUS_PATTERNS = [
    r'(^|\s)rm\s+-rf', r'(^|\s)dd\s+', r'(^|\s)mkfs', r'(^|\s)chmod\s+\d{3}\s+/', r'(^|\s)shutdown\b', r'(^|\s)reboot\b'
]
DANGEROUS_RE = re.compile('|'.join(DANGEROUS_PATTERNS), re.IGNORECASE)

class ToolingHandler(BaseHandler):
    def __init__(self):
        super().__init__(name='ToolingHandler', description='Executes shell commands in an ephemeral sandbox copy of the workspace')

    def _is_safe(self, command: str) -> bool:
        if not command or not command.strip():
            return False
        if DANGEROUS_RE.search(command):
            return False
        return True

    def execute(self, step_goal: str, args: dict, state: SharedSessionState):
        command = args.get('command')
        if not command:
            return AgentResponse(success=False, content='No command specified.', status_update='no-command')

        if not self._is_safe(command):
            return AgentResponse(success=False, content=f'Command appears dangerous or disallowed: {command}', status_update='dangerous-command')

        # create ephemeral copy of workspace
        src = Path(state.workspace_context.path)
        tmpdir = Path(tempfile.mkdtemp(prefix='sovereign_sandbox_'))
        try:
            # copy files (excluding .sovereign_flight.json to avoid growth)
            for p in src.rglob('*'):
                rel = p.relative_to(src)
                dest = tmpdir / rel
                if p.is_dir():
                    dest.mkdir(parents=True, exist_ok=True)
                else:
                    # ensure parent exists
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    if p.name == '.sovereign_flight.json':
                        continue
                    shutil.copy2(p, dest)
            # execute command in tmpdir
            result = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=tmpdir, timeout=30)
            stdout = result.stdout or ''
            stderr = result.stderr or ''
            exit_code = result.returncode
            
            # Format output using OutputFormatter for clean display
            formatted_content = OutputFormatter.format_command_result(command, exit_code, stdout, stderr)
            
            # Enhanced failure detection - not just exit code
            has_error_indicators = stderr and any(
                indicator in stderr.lower() 
                for indicator in ['error:', 'invalid', 'command not found', 'usage:', 'illegal option', 'invalid option']
            )
            
            # Command is successful if exit code is 0 AND no error indicators
            is_success = (exit_code == 0) and not has_error_indicators
            
            return AgentResponse(
                success=is_success, 
                content=formatted_content, 
                status_update='completed' if is_success else 'failed', 
                artifacts_created={'sandbox_path': str(tmpdir), 'exit_code': exit_code, 'has_stderr': bool(stderr.strip())}
            )
        except subprocess.TimeoutExpired:
            return AgentResponse(success=False, content='Command timed out.', status_update='timeout')
        except Exception as e:
            return AgentResponse(success=False, content=f'Exception during execution: {e}', status_update='error')