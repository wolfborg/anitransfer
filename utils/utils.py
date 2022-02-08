"""Functions that are still too small for their own file."""

# default imports
import json
import math
import time
from typing import Dict, Union, Optional

# internal imports
from utils.statistics import Statistics


def format_log(fields: Dict[str, Union[str, int]]) -> str:
    """Format a dictionary to a JSON string ready for logging."""
    return json.dumps(fields, ensure_ascii=False)


class JikanDelay:
    """Singleton helper class to store the global delay timer."""

    _instance = None
    time = 0  # type: float

    def __new__(cls) -> "JikanDelay":
        """Singleton contructor of the JikanDelay instance."""
        if cls._instance is None:
            cls._instance = super(JikanDelay, cls).__new__(cls)
            cls.time = time.monotonic()
        return cls._instance

    def check(self, delay: int, statistics: Optional[Statistics] = None) -> None:
        """Ensure the delay between API requests of Jikan is enforced."""
        now = time.monotonic()
        delta = math.floor(now - self.time)
        diff = delay - delta
        if delta < delay:
            time.sleep(diff)
            if statistics:
                statistics.increment("time_spent_waiting", diff)
        self.time = time.monotonic()
