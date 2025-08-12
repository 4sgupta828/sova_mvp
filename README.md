# Sovereign Agent MVP

Minimal local MVP of the Sovereign Coding Agent (safe, schema-driven, plugin-discovery).

## Features
- Dynamic handler discovery (handlers folder)
- Pydantic-validated TaskPlan
- Simple CognitiveCore with a fake LLM (replaceable)
- Sandboxed ToolingHandler using ephemeral workspace copies
- Flight recorder (JSON) persisted in workspace
- CLI entrypoint: `python -m sovereign_agent.main [workspace]`

## Requirements
- Python 3.9+
- Install: `pip install -r requirements.txt`

## Quick start
1. `pip install -r requirements.txt`
2. `python -m sovereign_agent.main ./example_workspace`
3. In the CLI, try: `list files` or `exit`

