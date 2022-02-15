"""Implementation of exporters."""

# default imports
import xml.etree.cElementTree as ET
from typing import Any, List, Optional, Dict, Union

# 3rd party imports
from defusedxml import minidom

# internal imports
from utils.caches import MappingCache

MAPPING = {
    "watched": "Completed",
    "watching": "Watching",
    "want to watch": "Plan to Watch",
    "stalled": "On-Hold",
    "dropped": "Dropped",
    "won't watch": None,
}


class AnimeExporter:
    """Export converted anime into a myanimelist.net-like format."""

    username = ""
    anime_to_export = []  # type: List[Dict[str, Optional[Union[str, int]]]]
    cache = None  # type: MappingCache

    def __init__(self, username: str, cache_file: str) -> None:
        """Create a new AnimeExporter."""
        self.cache = MappingCache(cache_file)
        self.username = username

    def add(self, anime: Any) -> bool:
        """Add an anime entry to the export that will be rendered.

        Returns False if an unsupported status was filtered,
        True otherwise.
        """
        if MAPPING[anime["status"]]:
            self.anime_to_export.append(anime)
            return True
        return False

    def export(self, filepath: str) -> None:
        """Write the export to a file."""
        root = ET.Element("myanimelist")
        info = ET.SubElement(root, "myinfo")

        # username
        username = ET.SubElement(info, "user_name")
        username.text = self.username

        # total anime watched
        total = ET.SubElement(info, "user_total_anime")
        total.text = str(len(self.anime_to_export))

        # anime section
        for anime in self.anime_to_export:
            entry = ET.SubElement(root, "anime")

            # ID
            ET.SubElement(entry, "series_animedb_id").text = self.cache.lookup(
                str(anime["name"])
            )

            # title
            ET.SubElement(entry, "series_title").text = str(anime["name"])

            # progress
            ET.SubElement(entry, "my_watched_episodes").text = str(anime["eps"])

            # start date
            ET.SubElement(entry, "my_start_date").text = _fill_date(
                anime.get("started")
            )

            # completed date
            ET.SubElement(entry, "my_finish_date").text = _fill_date(
                anime.get("completed")
            )

            # score
            # anime-planet.com defaults to 0.5-5 ratings, in steps of 0.5
            # myanimelist.net defaults to ratings of 1-10, in steps of 1
            score = ET.SubElement(entry, "my_score ")
            if anime["rating"]:
                score.text = str(int(anime["rating"] * 2))
            else:
                score.text = str(0)

            # status
            ET.SubElement(entry, "my_status").text = MAPPING[str(anime["status"])]

            # amount of times watched
            ET.SubElement(entry, "my_times_watched").text = _convert_times_watched(
                anime.get("times")
            )

        dom = minidom.parseString(ET.tostring(root))
        pretty_dom = dom.toprettyxml(indent="\t", encoding="UTF-8")
        with open(filepath, "wb") as export_file:
            export_file.write(pretty_dom)


def _fill_date(date: Optional[Union[int, str]]) -> str:
    """Convert different datetime stamps between sites.

    Provide a default of 0000-00-00 if no date is found.
    """
    if not date or not isinstance(date, str):
        converted_date = "0000-00-00"
    else:
        # remove time and leave only date
        converted_date = date.split()[0]

    return converted_date


def _convert_times_watched(times: Optional[Union[int, str]]) -> str:
    """Convert different counting systems between sites.

    Provide a default of 0 if no amount is found.
    """
    # case: times is not assigned
    if not times:
        times = 0

    # case: times is a string
    if isinstance(times, str):
        if times.isdigit():
            times = int(times)
        else:
            times = 0

    if times > 1:
        times = times - 1

    return str(times)
