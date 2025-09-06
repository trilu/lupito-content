"""
JSON path resolver for safe nested data access
"""
from typing import Any, Optional, Union, List


def resolve_path(data: Any, path: str, default: Any = None) -> Any:
    """
    Safely resolve a dot-separated path in nested JSON data.
    
    Args:
        data: The JSON data (dict, list, or primitive)
        path: Dot-separated path (e.g., "data.brand.name")
        default: Value to return if path not found (default: None)
    
    Returns:
        The value at the path, or default if not found
    
    Examples:
        >>> data = {"data": {"brand": {"name": "Acana"}}}
        >>> resolve_path(data, "data.brand.name")
        'Acana'
        >>> resolve_path(data, "data.missing.field")
        None
        >>> resolve_path(data, "data.missing.field", "N/A")
        'N/A'
    """
    if not path:
        return data
    
    try:
        current = data
        parts = path.split('.')
        
        for part in parts:
            if current is None:
                return default
            
            # Handle array index notation: field[0]
            if '[' in part and ']' in part:
                field, index_str = part.split('[')
                index = int(index_str.rstrip(']'))
                
                # First get the field
                if field:
                    if isinstance(current, dict):
                        current = current.get(field)
                    else:
                        return default
                
                # Then get the index
                if isinstance(current, (list, tuple)):
                    if -len(current) <= index < len(current):
                        current = current[index]
                    else:
                        return default
                else:
                    return default
            
            # Regular field access
            elif isinstance(current, dict):
                current = current.get(part)
            else:
                return default
        
        return current if current is not None else default
    
    except (KeyError, IndexError, TypeError, ValueError):
        return default


def resolve_multiple(data: Any, paths: List[str], default: Any = None) -> Any:
    """
    Try multiple paths and return the first non-None value.
    
    Args:
        data: The JSON data
        paths: List of paths to try in order
        default: Value to return if all paths fail
    
    Returns:
        First successful value or default
    
    Example:
        >>> resolve_multiple(data, ["data.name", "data.title", "data.label"])
    """
    for path in paths:
        value = resolve_path(data, path)
        if value is not None:
            return value
    return default


def extract_all(data: Any, path: str) -> List[Any]:
    """
    Extract all values from an array path.
    
    Args:
        data: The JSON data
        path: Path to an array field
    
    Returns:
        List of values, or empty list if not found
    
    Example:
        >>> data = {"data": {"variations": [{"weight": "1kg"}, {"weight": "5kg"}]}}
        >>> extract_all(data, "data.variations")
        [{"weight": "1kg"}, {"weight": "5kg"}]
    """
    result = resolve_path(data, path, [])
    if isinstance(result, list):
        return result
    elif result is not None:
        return [result]  # Wrap single value in list
    return []


def extract_values(data: Any, array_path: str, value_path: str) -> List[Any]:
    """
    Extract specific values from objects in an array.
    
    Args:
        data: The JSON data
        array_path: Path to the array
        value_path: Path within each array item
    
    Returns:
        List of extracted values
    
    Example:
        >>> data = {"data": {"variations": [{"weight_label": "1kg"}, {"weight_label": "5kg"}]}}
        >>> extract_values(data, "data.variations", "weight_label")
        ['1kg', '5kg']
    """
    items = extract_all(data, array_path)
    values = []
    
    for item in items:
        value = resolve_path(item, value_path)
        if value is not None:
            values.append(value)
    
    return values


def safe_float(value: Any, default: float = None) -> Optional[float]:
    """
    Safely convert a value to float.
    
    Args:
        value: Value to convert
        default: Default if conversion fails
    
    Returns:
        Float value or default
    """
    if value is None:
        return default
    
    try:
        # Handle string numbers with currency symbols
        if isinstance(value, str):
            # Remove common currency symbols and whitespace
            cleaned = value.replace('£', '').replace('€', '').replace('$', '').strip()
            cleaned = cleaned.replace(',', '')  # Remove thousands separator
            return float(cleaned)
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value: Any, default: int = None) -> Optional[int]:
    """
    Safely convert a value to int.
    
    Args:
        value: Value to convert
        default: Default if conversion fails
    
    Returns:
        Int value or default
    """
    if value is None:
        return default
    
    try:
        # Try float first to handle "1.0" -> 1
        return int(float(value))
    except (ValueError, TypeError):
        return default


def safe_bool(value: Any, default: bool = False) -> bool:
    """
    Safely convert a value to boolean.
    
    Args:
        value: Value to convert
        default: Default if conversion fails
    
    Returns:
        Boolean value
    """
    if value is None:
        return default
    
    if isinstance(value, bool):
        return value
    
    if isinstance(value, str):
        value_lower = value.lower().strip()
        if value_lower in ('true', 'yes', 'y', '1', 'on'):
            return True
        elif value_lower in ('false', 'no', 'n', '0', 'off'):
            return False
    
    try:
        return bool(value)
    except:
        return default