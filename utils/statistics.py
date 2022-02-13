"""Implementation of statistics."""

# default imports
from typing import Dict

# 3rd party imports
from rich.console import Console
from rich.table import Table


class Statistics:
    """Hold statistics about the current anitransfer run."""

    _instance = None
    counters = {}  # type: Dict[str, int]

    def __new__(cls) -> "Statistics":
        """Singleton constructor of the Statistics instance."""
        if cls._instance is None:
            cls._instance = super(Statistics, cls).__new__(cls)
            cls.counters = {
                "entries_processed": 0,
                "entries_matched_manually": 0,
                "entries_matched_using_jikan": 0,
                "entries_matched_using_cache": 0,
                "entries_matched_using_blacklist": 0,
                "entries_unmatched": 0,
                "entries_unsupported": 0,
                "jikan_requests_total": 0,
                "jikan_requests_cached": 0,
                "jikan_requests_failed": 0,
                "time_spent_waiting": 0,
            }

        return cls._instance

    def increment(self, name: str, amount: int = 1) -> None:
        """Increment value for a given statistic name."""
        self.counters.update({name: self.counters.get(name, 0) + amount})

    def print_summary(self) -> None:
        """Print a formatted summary of the statistics."""
        table = Table(
            title="anitransfer summary",
            highlight=True,
            row_styles=["", "dim"]
            )

        table.add_column("Section")
        table.add_column("Action")
        table.add_column("Count", justify="right")

        table.add_row("Entries", "processed", str(self.counters["entries_processed"]))
        table.add_row("Entries", "unmatched", str(self.counters["entries_unmatched"]))
        table.add_row(
            "Entries",
            "dropped due to unsupported status",
            str(self.counters["entries_unsupported"]),
        )
        table.add_row(
            "Matches",
            "matched via Jikan",
            str(self.counters["entries_matched_using_jikan"]),
        )
        table.add_row(
            "Matches",
            "matched via cache",
            str(self.counters["entries_matched_using_cache"]),
        )
        table.add_row(
            "Matches",
            "excluded via blacklist",
            str(self.counters["entries_matched_using_blacklist"]),
        )
        table.add_row(
            "Matches",
            "matched manually",
            str(self.counters["entries_matched_manually"]),
        )
        table.add_row(
            "Requests", "requests made", str(self.counters["jikan_requests_total"])
        )
        table.add_row(
            "Requests",
            "requests skipped due to cache",
            str(self.counters["jikan_requests_cached"]),
        )
        table.add_row(
            "Requests", "requests failed", str(self.counters["jikan_requests_failed"])
        )
        table.add_row(
            "Time", "spent waiting (seconds)", str(self.counters["time_spent_waiting"])
        )

        console = Console()
        console.print(table, new_line_start=True)
