import json
import time
import os
import logging
from typing import Dict, Any, Optional, Literal
from pydantic import BaseModel, Field, ValidationError
from openai import OpenAI
import anthropic
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

class LLMResponse(BaseModel):
    content: str
    success: bool
    metadata: Dict[str, Any] = Field(default_factory=dict)
    truncated: bool = False
    error: Optional[str] = None

class LLMClient:
    """Multi-provider LLM client with retry logic and validation."""
    
    def __init__(
        self, 
        provider: Literal["openai", "anthropic"], 
        model: str,
        api_key: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        if not provider or not model:
            raise ValueError("Provider and model must be specified")
        
        self.provider = provider
        self.model = model
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Initialize client
        if provider == "openai":
            api_key = api_key or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OpenAI API key required")
            self.client = OpenAI(api_key=api_key)
            
        elif provider == "anthropic":
            api_key = api_key or os.getenv("ANTHROPIC_API_KEY")  
            if not api_key:
                raise ValueError("Anthropic API key required")
            self.client = anthropic.Anthropic(api_key=api_key)
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    def _is_truncated_response(self, content: str) -> bool:
        """Detect if response appears truncated."""
        if not content or len(content.strip()) < 10:
            return True
            
        truncation_indicators = [
            "I apologize, but it seems my response was cut off",
            "Due to length limitations",
            "The response was truncated",
            "...",  # Common truncation indicator
        ]
        
        content_lower = content.lower()
        for indicator in truncation_indicators:
            if indicator.lower() in content_lower:
                return True
                
        return False

    def _validate_response(self, content: str) -> tuple[bool, Optional[str]]:
        """Validate response completeness and quality."""
        if not content or not content.strip():
            return False, "Empty response"
            
        if self._is_truncated_response(content):
            return False, "Response appears truncated"
            
        if len(content.strip()) < 5:
            return False, "Response too short"
            
        return True, None

    def _make_api_call(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """Make actual API call to provider."""
        try:
            if self.provider == "openai":
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.0
                )
                content = response.choices[0].message.content
                metadata = {
                    "usage": response.usage.model_dump() if response.usage else {},
                    "finish_reason": response.choices[0].finish_reason
                }
                
            elif self.provider == "anthropic":
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                    temperature=0.0
                )
                content = response.content[0].text if response.content else ""
                metadata = {
                    "usage": {
                        "input_tokens": response.usage.input_tokens if response.usage else 0,
                        "output_tokens": response.usage.output_tokens if response.usage else 0
                    },
                    "stop_reason": response.stop_reason
                }
            
            # Validate response
            is_valid, error = self._validate_response(content)
            
            return LLMResponse(
                content=content or "",
                success=is_valid,
                metadata=metadata,
                truncated=self._is_truncated_response(content or ""),
                error=error
            )
            
        except Exception as e:
            logger.error(f"API call failed: {e}")
            return LLMResponse(
                content="",
                success=False,
                error=str(e)
            )

    def call(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """Make LLM call with retry logic."""
        if not system_prompt or not user_prompt:
            return LLMResponse(
                content="",
                success=False,
                error="System prompt and user prompt are required"
            )
        
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                response = self._make_api_call(system_prompt, user_prompt)
                
                if response.success:
                    return response
                    
                # If truncated, try again with shorter prompt
                if response.truncated and attempt < self.max_retries - 1:
                    logger.warning(f"Response truncated on attempt {attempt + 1}, retrying...")
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                    
                last_error = response.error
                
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                
            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay * (attempt + 1))
        
        return LLMResponse(
            content="",
            success=False,
            error=f"Failed after {self.max_retries} attempts. Last error: {last_error}"
        )

    def call_with_structured_output(
        self, 
        system_prompt: str, 
        user_prompt: str, 
        output_schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call LLM and parse JSON response according to schema."""
        if not output_schema:
            raise ValueError("Output schema is required")
        
        # Add JSON formatting instructions
        json_prompt = f"{user_prompt}\n\nRespond with valid JSON matching this schema: {json.dumps(output_schema)}"
        
        response = self.call(system_prompt, json_prompt)
        
        if not response.success:
            return {"error": response.error, "success": False}
        
        try:
            # Try to extract JSON from response
            content = response.content.strip()
            
            # Handle code blocks
            if "```json" in content:
                start = content.find("```json") + 7
                end = content.find("```", start)
                if end != -1:
                    content = content[start:end].strip()
            elif "```" in content:
                start = content.find("```") + 3
                end = content.find("```", start)
                if end != -1:
                    content = content[start:end].strip()
            
            parsed = json.loads(content)
            parsed["success"] = True
            return parsed
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            return {"error": f"Invalid JSON response: {str(e)}", "success": False}

class LLMUseCase:
    """Enum for different LLM use cases."""
    PLANNING = "planning"
    CODE_GENERATION = "code_generation"  
    DEBUGGING = "debugging"
    GENERAL = "general"

class LLMConfigManager:
    """Manages different LLM configurations for different use cases."""
    
    def __init__(self):
        self.configs = {
            LLMUseCase.PLANNING: {
                "provider": "openai",
                "model": "gpt-4",
                "description": "Strategic planning and task orchestration"
            },
            LLMUseCase.CODE_GENERATION: {
                "provider": "openai", 
                "model": "gpt-4",
                "description": "Code generation and implementation"
            },
            LLMUseCase.DEBUGGING: {
                "provider": "anthropic",
                "model": "claude-3-5-sonnet-20241022",
                "description": "Problem analysis and debugging"
            },
            LLMUseCase.GENERAL: {
                "provider": "openai",
                "model": "gpt-4",
                "description": "General purpose tasks"
            }
        }

    def get_client(self, use_case: str) -> LLMClient:
        """Get appropriate LLM client for use case."""
        if use_case not in self.configs:
            use_case = LLMUseCase.GENERAL
        
        config = self.configs[use_case]
        return LLMClient(
            provider=config["provider"],
            model=config["model"]
        )

    def set_config(self, use_case: str, provider: str, model: str, description: str = ""):
        """Update configuration for a use case."""
        if not use_case or not provider or not model:
            raise ValueError("Use case, provider, and model are required")
        
        self.configs[use_case] = {
            "provider": provider,
            "model": model, 
            "description": description
        }