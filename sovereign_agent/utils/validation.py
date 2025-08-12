"""Validation utilities to prevent runtime errors."""

import logging
from typing import Any, Dict, List, Optional, Union, Callable

logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass

class Validator:
    """Comprehensive validation utilities."""
    
    @staticmethod
    def require_not_none(value: Any, name: str) -> Any:
        """Require value is not None."""
        if value is None:
            raise ValidationError(f"{name} cannot be None")
        return value
    
    @staticmethod
    def require_not_empty_string(value: str, name: str) -> str:
        """Require string is not None or empty."""
        if not value or not isinstance(value, str) or not value.strip():
            raise ValidationError(f"{name} must be a non-empty string")
        return value.strip()
    
    @staticmethod
    def require_type(value: Any, expected_type: type, name: str) -> Any:
        """Require value is of expected type."""
        if not isinstance(value, expected_type):
            raise ValidationError(f"{name} must be of type {expected_type.__name__}, got {type(value).__name__}")
        return value
    
    @staticmethod
    def require_dict(value: Any, name: str) -> Dict[str, Any]:
        """Require value is a dictionary."""
        if not isinstance(value, dict):
            raise ValidationError(f"{name} must be a dictionary, got {type(value).__name__}")
        return value
    
    @staticmethod
    def require_list(value: Any, name: str) -> List[Any]:
        """Require value is a list."""
        if not isinstance(value, list):
            raise ValidationError(f"{name} must be a list, got {type(value).__name__}")
        return value
    
    @staticmethod
    def require_non_empty_list(value: Any, name: str) -> List[Any]:
        """Require value is a non-empty list."""
        if not isinstance(value, list):
            raise ValidationError(f"{name} must be a list, got {type(value).__name__}")
        if len(value) == 0:
            raise ValidationError(f"{name} cannot be empty")
        return value
    
    @staticmethod
    def require_range(value: Union[int, float], min_val: Union[int, float], max_val: Union[int, float], name: str) -> Union[int, float]:
        """Require numeric value is within range."""
        if not isinstance(value, (int, float)):
            raise ValidationError(f"{name} must be a number, got {type(value).__name__}")
        if value < min_val or value > max_val:
            raise ValidationError(f"{name} must be between {min_val} and {max_val}, got {value}")
        return value
    
    @staticmethod
    def require_one_of(value: Any, allowed_values: List[Any], name: str) -> Any:
        """Require value is one of allowed values."""
        if value not in allowed_values:
            raise ValidationError(f"{name} must be one of {allowed_values}, got {value}")
        return value
    
    @staticmethod
    def require_has_attribute(obj: Any, attr_name: str, obj_name: str = "object") -> Any:
        """Require object has specified attribute."""
        if not hasattr(obj, attr_name):
            raise ValidationError(f"{obj_name} must have attribute '{attr_name}'")
        return obj
    
    @staticmethod
    def require_callable(value: Any, name: str) -> Callable:
        """Require value is callable."""
        if not callable(value):
            raise ValidationError(f"{name} must be callable")
        return value

def safe_get_attribute(obj: Any, attr_name: str, default: Any = None) -> Any:
    """Safely get attribute from object with default."""
    try:
        return getattr(obj, attr_name, default)
    except Exception as e:
        logger.warning(f"Failed to get attribute '{attr_name}': {e}")
        return default

def safe_dict_get(d: Dict[str, Any], key: str, default: Any = None) -> Any:
    """Safely get value from dictionary with type checking."""
    if not isinstance(d, dict):
        logger.warning(f"Expected dictionary, got {type(d).__name__}")
        return default
    
    return d.get(key, default)

def validate_json_structure(data: Dict[str, Any], required_keys: List[str], name: str = "JSON") -> Dict[str, Any]:
    """Validate JSON structure has required keys."""
    if not isinstance(data, dict):
        raise ValidationError(f"{name} must be a dictionary")
    
    missing_keys = [key for key in required_keys if key not in data]
    if missing_keys:
        raise ValidationError(f"{name} missing required keys: {missing_keys}")
    
    return data

def clean_string(value: Any) -> str:
    """Clean and normalize string value."""
    if value is None:
        return ""
    
    if not isinstance(value, str):
        value = str(value)
    
    return value.strip()

def safe_int_conversion(value: Any, default: int = 0) -> int:
    """Safely convert value to integer."""
    try:
        return int(value)
    except (ValueError, TypeError):
        logger.warning(f"Failed to convert '{value}' to int, using default {default}")
        return default

def safe_float_conversion(value: Any, default: float = 0.0) -> float:
    """Safely convert value to float."""
    try:
        return float(value)
    except (ValueError, TypeError):
        logger.warning(f"Failed to convert '{value}' to float, using default {default}")
        return default