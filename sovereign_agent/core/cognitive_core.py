import json
import logging
from typing import List, Optional, Dict, Any
from sovereign_agent.core.models import TaskPlan, HandlerStepModel
from sovereign_agent.core.state import SharedSessionState
from sovereign_agent.handlers.base import BaseHandler
from sovereign_agent.integrations.llm_client import LLMClient, LLMConfigManager, LLMUseCase

logger = logging.getLogger(__name__)


class IntelligentLLM:
    """Advanced LLM-powered planning with validation and error handling."""
    
    def __init__(self, llm_config_manager: Optional[LLMConfigManager] = None):
        self.config_manager = llm_config_manager or LLMConfigManager()
    
    def _validate_plan_structure(self, plan_data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate that plan has required structure."""
        if not isinstance(plan_data, dict):
            return False, "Plan must be a dictionary"
        
        required_fields = ['overall_goal', 'steps']
        for field in required_fields:
            if field not in plan_data:
                return False, f"Missing required field: {field}"
        
        if not isinstance(plan_data['steps'], list):
            return False, "Steps must be a list"
        
        if not plan_data['steps']:
            return False, "At least one step is required"
        
        # Validate each step
        for i, step in enumerate(plan_data['steps']):
            if not isinstance(step, dict):
                return False, f"Step {i} must be a dictionary"
            
            step_required_fields = ['handler_name', 'step_goal']
            for field in step_required_fields:
                if field not in step:
                    return False, f"Step {i} missing required field: {field}"
            
            if not isinstance(step.get('input_args', {}), dict):
                return False, f"Step {i} input_args must be a dictionary"
        
        return True, None
    
    
    def plan_from_input(self, user_input: str, capabilities: List[dict], 
                       workspace_json: dict, conversation: List[dict]) -> str:
        """Generate execution plan using LLM with fallback to heuristics."""
        
        if not user_input or not user_input.strip():
            return json.dumps({
                'overall_goal': 'Handle empty request', 
                'steps': [], 
                'confidence': 0.0, 
                'reasoning': 'Empty or invalid input provided.'
            })
        
        try:
            # Get LLM client for planning
            llm_client = self.config_manager.get_client(LLMUseCase.PLANNING)
            
            # Create prompts using enhanced _build_prompt
            system_prompt, user_prompt = self._build_prompt(
                user_input, capabilities, workspace_json, conversation
            )
            
            # Call LLM
            response = llm_client.call(system_prompt, user_prompt)
            
            if not response.success:
                logger.error(f"LLM planning failed: {response.error}")
                return json.dumps({
                    'overall_goal': 'Failed to create plan', 
                    'steps': [], 
                    'confidence': 0.0, 
                    'reasoning': f'LLM error: {response.error}'
                })
            
            # Parse and validate response
            try:
                plan_data = json.loads(response.content)
                
                # Validate structure
                is_valid, error = self._validate_plan_structure(plan_data)
                if not is_valid:
                    logger.error(f"Invalid plan structure: {error}")
                    return json.dumps({
                        'overall_goal': 'Invalid plan structure', 
                        'steps': [], 
                        'confidence': 0.0, 
                        'reasoning': f'Validation error: {error}'
                    })
                
                return json.dumps(plan_data)
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response as JSON: {e}")
                return json.dumps({
                    'overall_goal': 'Failed to parse response', 
                    'steps': [], 
                    'confidence': 0.0, 
                    'reasoning': f'JSON parse error: {str(e)}'
                })
            
        except Exception as e:
            logger.error(f"Error in LLM planning: {e}")
            return json.dumps({
                'overall_goal': 'Planning error', 
                'steps': [], 
                'confidence': 0.0, 
                'reasoning': f'Exception: {str(e)}'
            })

class CognitiveCore:
    def __init__(self, handlers: List[BaseHandler]):
        # build capability list
        if not handlers:
            raise ValueError("At least one handler is required")
        
        self.handler_capabilities = {}
        for handler in handlers:
            if not handler or not hasattr(handler, 'get_capabilities'):
                logger.warning(f"Invalid handler: {handler}")
                continue
            
            capabilities = handler.get_capabilities()
            if not isinstance(capabilities, dict) or 'name' not in capabilities:
                logger.warning(f"Handler {handler} has invalid capabilities")
                continue
                
            self.handler_capabilities[capabilities['name']] = capabilities
        
        if not self.handler_capabilities:
            raise ValueError("No valid handlers provided")
        
        # Initialize LLM
        try:
            self.llm = IntelligentLLM()
            logger.info("Initialized with intelligent LLM")
        except Exception as e:
            logger.error(f"Failed to initialize intelligent LLM: {e}")
            raise

    def _build_prompt(self, user_input: str, capabilities: List[dict], 
                     workspace_json: dict, conversation: List[dict]) -> tuple[str, str]:
        """Build enhanced system and user prompts for planning."""
        
        system_prompt = """You are the **Cognitive Core** of a Sovereign Coding Agent.
Your role is to translate user requests into **precise, optimized, multi-step TaskPlans** in JSON format.

**MISSION PRINCIPLE:**
- Act as a **strategic planner** — not just a task lister
- Ensure every step moves the agent measurably closer to the user's ultimate goal
- Minimize redundant steps while preserving logical completeness

**CRITICAL REQUIREMENTS:**
1. Generate ONLY valid JSON - no explanations, commentary, or extra text
2. Every step must be achievable via exactly one handler call
3. Include ALL required fields: overall_goal, steps (array), confidence (0.0-1.0), reasoning
4. Each step must have: handler_name, step_goal, input_args (dict)
5. Use only available handlers from capabilities list
6. Be strategic - minimize redundant steps while ensuring completeness

**SAFETY & AUTONOMY RULES:**
- Never skip an obvious prerequisite step
- If ambiguity exists, insert a clarification or research step before execution
- Prefer deterministic, low-risk actions early in the plan

**RESPONSE FORMAT (JSON only):**
{
  "overall_goal": "Clear description of what will be accomplished",
  "steps": [
    {
      "handler_name": "HandlerName",
      "step_goal": "What this step achieves",
      "input_args": {"key": "value"}
    }
  ],
  "confidence": 0.8,
  "reasoning": "Why this plan will work"
}"""

        user_prompt = f"""**ANALYZE REQUEST:** "{user_input}"

**AVAILABLE HANDLERS:**
{json.dumps(capabilities, indent=2)}

**WORKSPACE CONTEXT:**
Path: {workspace_json.get('path', 'unknown')}
Files: {len(workspace_json.get('file_tree_summary', {}).get('files', []))} files
Structure: {', '.join(workspace_json.get('file_tree_summary', {}).get('files', [])[:5]) + ('...' if len(workspace_json.get('file_tree_summary', {}).get('files', [])) > 5 else '')}

**RECENT CONVERSATION:**
{json.dumps(conversation[-3:], indent=2)}

**SOVEREIGN CHAIN-OF-THOUGHT (reason before output):**
- Step A: Restate the true end goal in your own words
- Step B: Identify missing information or constraints
- Step C: Decide the most efficient ordering of actions
- Step D: Break the plan into atomic steps — each achievable via exactly one handler call
- Step E: For each step, specify step_goal and input_args

Generate a TaskPlan JSON that accomplishes the user's request using available handlers."""

        return system_prompt, user_prompt

    def orchestrate(self, user_input: str, state: SharedSessionState) -> Optional[TaskPlan]:
        """Orchestrate user request into executable task plan."""
        
        if not user_input or not user_input.strip():
            logger.warning("Empty user input provided")
            return None
            
        if not state:
            logger.error("SharedSessionState is required")
            return None
        
        try:
            # Validate state has required attributes
            if not hasattr(state, 'workspace_context') or not hasattr(state, 'conversation_history'):
                logger.error("State missing required attributes")
                return None
                
            workspace_json = state.workspace_context.to_json()
            conversation = state.conversation_history[-5:] if state.conversation_history else []
            
            # Get plan from LLM using enhanced prompt
            system_prompt, user_prompt = self._build_prompt(
                user_input,
                list(self.handler_capabilities.values()),
                workspace_json,
                conversation
            )
            
            # Get LLM client and make call
            llm_client = self.llm.config_manager.get_client(LLMUseCase.PLANNING)
            response = llm_client.call(system_prompt, user_prompt)
            
            if not response.success:
                logger.error(f"LLM call failed: {response.error}")
                return None
            
            plan_text = response.content
            
            if not plan_text:
                logger.error("LLM returned empty plan")
                return None
            
            # Parse plan
            try:
                plan_data = json.loads(plan_text)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON from LLM: {e}")
                return None
            
            # Validate plan structure
            if not isinstance(plan_data, dict):
                logger.error("Plan must be a dictionary")
                return None
                
            if not plan_data.get('steps'):
                logger.warning("Plan has no steps")
                return None
            
            if not isinstance(plan_data['steps'], list):
                logger.error("Plan steps must be a list")
                return None
            
            # Convert steps to HandlerStepModel with validation
            steps = []
            for i, step_data in enumerate(plan_data['steps']):
                try:
                    if not isinstance(step_data, dict):
                        logger.error(f"Step {i} must be a dictionary")
                        continue
                    
                    # Ensure required fields exist
                    if 'handler_name' not in step_data:
                        logger.error(f"Step {i} missing handler_name")
                        continue
                    if 'step_goal' not in step_data:
                        logger.error(f"Step {i} missing step_goal")
                        continue
                    
                    # Ensure input_args is a dict
                    if 'input_args' not in step_data:
                        step_data['input_args'] = {}
                    elif not isinstance(step_data['input_args'], dict):
                        logger.warning(f"Step {i} input_args not a dict, converting")
                        step_data['input_args'] = {}
                    
                    step = HandlerStepModel(**step_data)
                    steps.append(step)
                    
                except Exception as e:
                    logger.error(f"Error creating step {i}: {e}")
                    continue
            
            if not steps:
                logger.error("No valid steps in plan")
                return None
            
            # Create TaskPlan with validation
            try:
                task_plan = TaskPlan(
                    overall_goal=plan_data.get('overall_goal', ''),
                    steps=steps,
                    confidence=float(plan_data.get('confidence', 1.0)),
                    reasoning=plan_data.get('reasoning', '')
                )
                
                logger.info(f"Created task plan with {len(steps)} steps")
                return task_plan
                
            except Exception as e:
                logger.error(f"Error creating TaskPlan: {e}")
                return None
            
        except Exception as e:
            logger.error(f"Error in orchestrate: {e}")
            return None
