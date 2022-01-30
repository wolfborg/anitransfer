"""Functions that are still too small for their own file."""

# default imports
import json
from typing import Dict, Union


def format_log(fields: Dict[str, Union[str, int]]) -> str:
    """Format a dictionary to a JSON string ready for logging."""
    return json.dumps(fields, ensure_ascii=False)
