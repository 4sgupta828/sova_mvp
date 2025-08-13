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
    def format_command_result(cls, command: str, exit_code: int, stdout: str, stderr: str, max_lines: int = 50) -> str:
        """Format command execution result for clean display."""
        
        # Enhance output with context if missing
        stdout = cls._enhance_output_context(command, stdout)
        
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
        # Don't truncate commands - show them in full for clarity
        # If very long (>200 chars), show on multiple lines for readability
        if len(command) > 200:
            # Break long commands at logical points (pipes, &&, ||)
            for sep in [' | ', ' && ', ' || ', '; ']:
                if sep in command:
                    parts = command.split(sep)
                    return f"{sep}\\n  ".join(parts)
        return command
    
    @classmethod
    def _format_output(cls, output: str, label: str, color: str, max_lines: int) -> str:
        """Format stdout/stderr output with truncation."""
        lines = output.strip().split('\n')
        
        # Smart truncation based on output size
        if len(lines) > max_lines:
            # Show first portion and last few lines for context
            first_chunk = lines[:max_lines - 5]
            last_chunk = lines[-3:]
            truncated_count = len(lines) - max_lines + 2
            
            displayed_lines = first_chunk + [
                f"{cls.DIM}",
                f"... ({truncated_count} more lines) ...",
                f"[Last few lines shown below]{cls.RESET}"
            ] + last_chunk
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
    def _enhance_output_context(cls, command: str, output: str) -> str:
        """Enhance output with missing context information."""
        if not output or not output.strip():
            return output
        
        # Check if output already has file context (filename:line_number: pattern)
        lines = output.strip().split('\n')
        has_context = False
        for line in lines[:3]:  # Check first 3 lines
            if ':' in line:
                parts = line.split(':')
                if len(parts) > 1 and parts[1].strip().isdigit():
                    has_context = True
                    break
        
        if has_context:
            # Output already has context, return as-is
            return output
        
        # If this looks like code search results without context, add helpful note
        if ('def ' in output or 'class ' in output or 'import ' in output) and 'find' in command.lower():
            context_note = f"{cls.DIM}Note: Output above lacks file context. For better results, use:\n  grep -n -H \"pattern\" *.py  # to see filename:line_number:match{cls.RESET}\n\n"
            return context_note + output
        
        return output
    
    @classmethod
    def format_error(cls, error_msg: str) -> str:
        """Format error message."""
        return f"{cls.RED}❌ Error:{cls.RESET} {error_msg}"
    
    @classmethod
    def format_success(cls, message: str) -> str:
        """Format success message."""
        return f"{cls.GREEN}✅{cls.RESET} {message}"