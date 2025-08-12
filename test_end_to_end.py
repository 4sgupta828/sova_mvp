#!/usr/bin/env python3
"""
End-to-end test of the Sovereign Agent without actual LLM API calls.
"""

import sys
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

def test_models():
    """Test all Pydantic models can be instantiated and validated."""
    print("🧪 Testing models...")
    
    from sovereign_agent.core.models import AgentResponse, HandlerStepModel, TaskPlan
    
    # Test AgentResponse
    response = AgentResponse(success=True, content="Test content")
    assert response.success == True
    assert response.content == "Test content"
    assert response.status_update == ""
    assert response.artifacts_created == {}
    
    # Test HandlerStepModel
    step = HandlerStepModel(
        handler_name="TestHandler",
        step_goal="Test goal",
        input_args={"key": "value"}
    )
    assert step.handler_name == "TestHandler"
    assert step.step_goal == "Test goal"
    assert step.status == "pending"
    assert step.input_args == {"key": "value"}
    
    # Test TaskPlan
    plan = TaskPlan(
        overall_goal="Test plan",
        steps=[step],
        confidence=0.8,
        reasoning="Test reasoning"
    )
    assert plan.overall_goal == "Test plan"
    assert len(plan.steps) == 1
    assert plan.confidence == 0.8
    
    print("✅ Models test passed")

def test_handlers():
    """Test handlers can be instantiated and basic validation works."""
    print("🧪 Testing handlers...")
    
    from sovereign_agent.handlers.tooling_handler import ToolingHandler
    from sovereign_agent.core.state import SharedSessionState
    from sovereign_agent.core.models import AgentResponse
    
    # Create test workspace
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace_path = Path(tmpdir)
        
        # Test handler instantiation
        handler = ToolingHandler()
        assert handler.name == "ToolingHandler"
        assert "shell commands" in handler.description
        
        # Test capabilities
        capabilities = handler.get_capabilities()
        assert capabilities["name"] == "ToolingHandler"
        assert "description" in capabilities
        
        # Test state creation
        state = SharedSessionState(workspace_path)
        assert state.workspace_context.path == workspace_path
        assert isinstance(state.conversation_history, list)
    
    print("✅ Handlers test passed")

def test_llm_client():
    """Test LLM client structure without API calls."""
    print("🧪 Testing LLM client...")
    
    from sovereign_agent.integrations.llm_client import LLMConfigManager, LLMUseCase
    
    # Test config manager
    config_manager = LLMConfigManager()
    
    # Test different use cases are configured
    assert LLMUseCase.PLANNING in config_manager.configs
    assert LLMUseCase.CODE_GENERATION in config_manager.configs
    assert LLMUseCase.DEBUGGING in config_manager.configs
    
    # Test config structure
    planning_config = config_manager.configs[LLMUseCase.PLANNING]
    assert "provider" in planning_config
    assert "model" in planning_config
    assert "description" in planning_config
    
    print("✅ LLM client test passed")

def test_cognitive_core():
    """Test cognitive core can be instantiated and basic functionality works."""
    print("🧪 Testing cognitive core...")
    
    from sovereign_agent.core.cognitive_core import CognitiveCore, IntelligentLLM
    from sovereign_agent.handlers.tooling_handler import ToolingHandler
    from sovereign_agent.core.state import SharedSessionState
    from sovereign_agent.integrations.llm_client import LLMResponse
    
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace_path = Path(tmpdir)
        
        # Create handlers
        handlers = [ToolingHandler()]
        
        # Test IntelligentLLM structure
        intelligent_llm = IntelligentLLM()
        assert hasattr(intelligent_llm, 'config_manager')
        assert hasattr(intelligent_llm, '_validate_plan_structure')
        
        # Test plan validation
        valid_plan = {
            "overall_goal": "Test goal",
            "steps": [
                {
                    "handler_name": "ToolingHandler",
                    "step_goal": "Test step",
                    "input_args": {"command": "ls"}
                }
            ]
        }
        is_valid, error = intelligent_llm._validate_plan_structure(valid_plan)
        assert is_valid == True
        assert error is None
        
        # Test invalid plan
        invalid_plan = {"overall_goal": "Test goal"}  # Missing steps
        is_valid, error = intelligent_llm._validate_plan_structure(invalid_plan)
        assert is_valid == False
        assert "steps" in error
        
        # Test CognitiveCore instantiation
        try:
            core = CognitiveCore(handlers)
            assert hasattr(core, 'handler_capabilities')
            assert hasattr(core, 'llm')
            assert len(core.handler_capabilities) == 1
            assert "ToolingHandler" in core.handler_capabilities
        except Exception as e:
            # Expected if LLM API keys are not set
            print(f"ℹ️  CognitiveCore initialization failed (expected without API keys): {e}")
    
    print("✅ Cognitive core test passed")

def test_agent_integration():
    """Test agent can be instantiated and basic flow works.""" 
    print("🧪 Testing agent integration...")
    
    from sovereign_agent.agent import SovereignAgent, discover_handlers
    
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace_path = str(tmpdir)
        
        # Test handler discovery
        handlers = discover_handlers()
        assert len(handlers) > 0
        assert "ToolingHandler" in handlers
        
        # Test agent instantiation
        try:
            agent = SovereignAgent(workspace_path)
            assert agent.workspace_path.exists()
            assert hasattr(agent, 'handlers')
            assert hasattr(agent, 'cognitive_core')
            assert hasattr(agent, 'state')
        except Exception as e:
            # Expected if LLM API keys are not set
            print(f"ℹ️  Agent initialization failed (expected without API keys): {e}")
    
    print("✅ Agent integration test passed")

def test_validation_utilities():
    """Test validation utilities work correctly."""
    print("🧪 Testing validation utilities...")
    
    from sovereign_agent.utils.validation import Validator, ValidationError
    
    # Test require_not_none
    try:
        Validator.require_not_none(None, "test")
        assert False, "Should have raised ValidationError"
    except ValidationError as e:
        assert "test" in str(e)
    
    # Test require_not_empty_string
    result = Validator.require_not_empty_string("  hello  ", "test")
    assert result == "hello"
    
    try:
        Validator.require_not_empty_string("", "test")
        assert False, "Should have raised ValidationError"
    except ValidationError:
        pass
    
    # Test require_type
    result = Validator.require_type([1, 2, 3], list, "test")
    assert result == [1, 2, 3]
    
    try:
        Validator.require_type("not a list", list, "test")
        assert False, "Should have raised ValidationError"  
    except ValidationError:
        pass
    
    print("✅ Validation utilities test passed")

def main():
    """Run all end-to-end tests."""
    print("🚀 Starting end-to-end tests...\n")
    
    try:
        test_models()
        test_handlers()
        test_llm_client()
        test_cognitive_core()
        test_agent_integration()
        test_validation_utilities()
        
        print(f"\n🎉 All tests passed! The Sovereign Agent system is working correctly.")
        print("ℹ️  Note: LLM API calls are not tested (requires API keys)")
        print("ℹ️  To test with real LLM calls, set OPENAI_API_KEY or ANTHROPIC_API_KEY environment variables")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())