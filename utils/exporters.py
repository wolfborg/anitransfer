"""Implementation of exporters."""

# default imports
import xml.etree.cElementTree as ET
from typing import Any, List, Optional, Dict, Union

# 3rd party imports
from rich import print
from defusedxml import minidom

# internal imports
from utils.caches import MappingCache

MAPPING = {
    "watched": "Completed",
    "watching": "Watching",
    "want to watch": "Plan to Watch",
    "stalled": "On-Hold",
    "dropped": "Dropped",
    "won't watch": None
}


class AnimeExporter:
    """Export converted anime into a myanimelist.net-like format."""

    username = ""
    anime_to_export = []  # type: List[Dict[str, Optional[Union[str, int]]]]
    cache = None  # type: MappingCache

    def __init__(self, username: str, cache_file: str) -> None:
        self.cache = MappingCache(cache_file)
        self.username = username

    def add(self, anime: Any) -> bool:
        """Add an anime entry to the export that will be rendered.

        Returns False if an unsupported status was filtered,
        True otherwise.
        """
        if MAPPING[anime['status']]:
            self.anime_to_export.append(anime)
            return True
        return False

    def export(self, filepath:str) -> None:
        """Write the export to a file."""
        root = ET.Element('myanimelist')
        info = ET.SubElement(root, 'myinfo')

        # username
        username = ET.SubElement(info, 'user_name')
        username.text = self.username

        # total anime watched
        total = ET.SubElement(info, 'user_total_anime')
        total.text = str(len(self.anime_to_export))

        # anime section
        for anime in self.anime_to_export:
            entry = ET.SubElement(root, 'anime')

            myanimelist_id = ET.SubElement(entry, 'series_animedb_id')
            myanimelist_id.text = self.cache.lookup(str(anime['name']))

            title = ET.SubElement(entry, 'series_title')
            title.text = str(anime['name'])

            watched = ET.SubElement(entry, 'my_watched_episodes')
            watched.text = str(anime['eps'])

            started = ET.SubElement(entry, 'my_start_date')
            if not anime['started']:
                started.text = "0000-00-00"
            else:
                started.text = str(anime['started']).split()[0]

            finished = ET.SubElement(entry, 'my_finish_date')
            if not anime['completed']:
                finished.text = "0000-00-00"
            else:
                finished.text = str(anime['completed']).split()[0]

            score = ET.SubElement(entry, 'my_score ')
            # anime-planet.com defaults to 0.5-5 ratings, in steps of 0.5
            # myanimelist.net defaults to ratings of 1-10, in steps of 1
            score.text = str(int(anime['rating'] * 2))

            status = ET.SubElement(entry, 'my_status')
            status.text = MAPPING[str(anime['status'])]

            times_watched = ET.SubElement(entry, 'my_times_watched')
            times = 0
            # logic taken as is from original
            if int(anime['times']) > 1:
                times = int(anime['times']) - 1
            times_watched.text = str(times)

        dom = minidom.parseString(ET.tostring(root))
        pretty_dom = dom.toprettyxml(indent='\t')
        with open(filepath, 'w', encoding='utf-8') as export_file:
            export_file.write(pretty_dom)
