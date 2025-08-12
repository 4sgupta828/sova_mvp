from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Any, Optional, Annotated
import uuid

class AgentResponse(BaseModel):
    success: bool
    content: str
    status_update: str = ''
    artifacts_created: Dict[str, Any] = Field(default_factory=dict)
    state_updates: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('content')
    @classmethod
    def content_must_not_be_none(cls, v):
        if v is None:
            return ''
        return v
    
    @field_validator('status_update')
    @classmethod
    def status_update_must_not_be_none(cls, v):
        if v is None:
            return ''
        return v

class HandlerStepModel(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    handler_name: str
    step_goal: str
    input_args: Dict[str, Any] = Field(default_factory=dict)
    status: str = 'pending'
    result: Optional[AgentResponse] = None
    
    @field_validator('handler_name')
    @classmethod
    def handler_name_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('handler_name cannot be empty')
        return v.strip()
    
    @field_validator('step_goal')
    @classmethod
    def step_goal_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('step_goal cannot be empty')
        return v.strip()
    
    @field_validator('status')
    @classmethod
    def status_must_be_valid(cls, v):
        valid_statuses = {'pending', 'running', 'completed', 'failed'}
        if v not in valid_statuses:
            raise ValueError(f'status must be one of {valid_statuses}')
        return v
    
    @field_validator('input_args')
    @classmethod
    def input_args_must_be_dict(cls, v):
        if v is None:
            return {}
        if not isinstance(v, dict):
            raise ValueError('input_args must be a dictionary')
        return v

class TaskPlan(BaseModel):
    plan_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    overall_goal: str
    steps: Annotated[List[HandlerStepModel], Field(min_length=1)]
    confidence: float = 1.0
    reasoning: str = ''
    
    @field_validator('overall_goal')
    @classmethod
    def overall_goal_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('overall_goal cannot be empty')
        return v.strip()
    
    @field_validator('confidence')
    @classmethod
    def confidence_must_be_valid(cls, v):
        if not isinstance(v, (int, float)):
            raise ValueError('confidence must be a number')
        if v < 0.0 or v > 1.0:
            raise ValueError('confidence must be between 0.0 and 1.0')
        return float(v)
    
    @field_validator('reasoning')
    @classmethod
    def reasoning_must_not_be_none(cls, v):
        if v is None:
            return ''
        return v
                                                                                                                                                        