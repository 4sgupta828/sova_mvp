"""Clean, minimal output formatting for command results."""

import re
from typing import Tuple

class OutputFormatter:
    """Minimal output formatter inspired by mvp5 patterns."""
    
    # Color codes
    GREEN = '\033[32m'
    RED = '\033[31m'
    CYAN = '\033[36m'
    YELLOW = '\033[33m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'
    
    @classmethod
    def format_command_result(cls, command: str, exit_code: int, stdout: str, stderr: str, max_lines: int = 20) -> str:
        """Format command execution result for clean display."""
        
        # Status indicator
        if exit_code == 0:
            status = f"{cls.GREEN}✅ SUCCESS{cls.RESET}"
        else:
            status = f"{cls.RED}❌ FAILED (exit code: {exit_code}){cls.RESET}"
        
        # Clean command display
        clean_cmd = cls._clean_command(command)
        
        result_parts = [
            f"{cls.CYAN}🔧 Command:{cls.RESET} {cls.BOLD}{clean_cmd}{cls.RESET}",
            f"{cls.CYAN}📊 Status:{cls.RESET} {status}"
        ]
        
        # Add stdout if present
        if stdout.strip():
            formatted_stdout = cls._format_output(stdout, "📤 Output", cls.GREEN, max_lines)
            result_parts.append(formatted_stdout)
        
        # Add stderr if present  
        if stderr.strip():
            formatted_stderr = cls._format_output(stderr, "⚠️  Error", cls.RED, max_lines)
            result_parts.append(formatted_stderr)
        
        return "\n\n".join(result_parts)
    
    @classmethod
    def _clean_command(cls, command: str) -> str:
        """Clean up command for display."""
        # Remove extra whitespace
        command = ' '.join(command.split())
        # Truncate very long commands
        if len(command) > 80:
            command = command[:77] + "..."
        return command
    
    @classmethod
    def _format_output(cls, output: str, label: str, color: str, max_lines: int) -> str:
        """Format stdout/stderr output with truncation."""
        lines = output.strip().split('\n')
        
        # Truncate if too many lines
        if len(lines) > max_lines:
            displayed_lines = lines[:max_lines]
            truncated_count = len(lines) - max_lines
            displayed_lines.append(f"{cls.DIM}... ({truncated_count} more lines){cls.RESET}")
            lines = displayed_lines
        
        # Format each line with proper indentation
        formatted_lines = [f"{cls.CYAN}{label}:{cls.RESET}"]
        
        for line in lines:
            # Escape any special characters for safe display
            safe_line = cls._escape_line(line)
            
            # Truncate very long lines
            if len(safe_line) > 120:
                safe_line = safe_line[:117] + "..."
            
            # Add line with proper indentation and color
            formatted_lines.append(f"  {color}{safe_line}{cls.RESET}")
        
        return "\n".join(formatted_lines)
    
    @classmethod
    def _escape_line(cls, line: str) -> str:
        """Escape special characters for safe terminal display."""
        # Remove ANSI color codes if present
        line = re.sub(r'\x1b\[[0-9;]*m', '', line)
        # Replace tabs with spaces
        line = line.replace('\t', '    ')
        # Remove any control characters except newlines
        line = ''.join(char for char in line if ord(char) >= 32 or char in '\n\r')
        return line
    
    @classmethod
    def format_step_header(cls, step_num: int, total_steps: int, step_goal: str, handler_name: str) -> str:
        """Format step execution header."""
        return f"\n{cls.BOLD}--- Step {step_num}/{total_steps}: {handler_name} ---{cls.RESET}\n{cls.CYAN}Goal:{cls.RESET} {step_goal}"
    
    @classmethod
    def format_plan_header(cls, overall_goal: str) -> str:
        """Format plan execution header."""
        return f"\n{cls.BOLD}🤖 Executing Plan:{cls.RESET} {overall_goal}"
    
    @classmethod
    def format_error(cls, error_msg: str) -> str:
        """Format error message."""
        return f"{cls.RED}❌ Error:{cls.RESET} {error_msg}"
    
    @classmethod
    def format_success(cls, message: str) -> str:
        """Format success message."""
        return f"{cls.GREEN}✅{cls.RESET} {message}"