"""Implementations of caches."""

# default imports
import datetime
import json
import hashlib
import logging
import os
from typing import Any, Dict, Optional

# 3rd party imports
from appdirs import user_cache_dir
from dateutil.parser import parse
from .utils import format_log


class JikanResultCache:
    """Implement a hash-addressed cache for Jikan results.

    The cache uses hashes instead of strings because anime like
    to use funny unicode symbols in their name. We do not want
    those on our users' filesystems just in case they hit an
    edge-case.
    """

    location = ""
    _supported_types = ["anime_title", "anime_search"]

    def __init__(self) -> None:
        """Create a new JikanResultCache."""
        self.location = os.path.join(user_cache_dir(), "anitransfer", "jikan_cache")

    def add(self, name: str, item_type: str, item: Dict[str, Any]) -> None:
        """Cache a Jikan API result."""
        self._verify_type_is_supported(item_type)
        key = _calculate_cache_key(name)
        cache_location = os.path.join(self.location, item_type)
        os.makedirs(cache_location, exist_ok=True)
        location = os.path.join(cache_location, f"{key}.json")

        with open(location, "w", encoding="utf8") as cache_entry:
            json.dump(item, cache_entry, indent=2, sort_keys=False)

        entry = format_log({"name": name, "item_type": item_type, "key": key})
        logging.info("Added to cache: %s", entry)

    def lookup(self, name: str, item_type: str) -> Optional[Dict[str, Any]]:
        """Look for an unexpired entry in the cache."""
        self._verify_type_is_supported(item_type)
        key = _calculate_cache_key(name)
        cache_location = os.path.join(self.location, item_type)
        location = os.path.join(cache_location, f"{key}.json")

        try:
            with open(location, 'r', encoding='utf8') as cache_entry:
                entry = json.load(cache_entry)  # type: Dict[str, Any]
                expiry_date = entry['headers']['Expires']
        # FileNotFoundError: there is no such cache entry
        # KeyError: there is no expiration date in the entry
        # both of those will cause a cache miss
        except (FileNotFoundError, KeyError):
            return None

        date = parse(expiry_date)
        now = datetime.datetime.now(datetime.timezone.utc)
        if now > date:
            return None

        message = format_log({'name': name, 'item_type': item_type, 'key': key})
        logging.info('Jikan Cache hit: %s', message)
        return entry

    def _verify_type_is_supported(self, item_type: str) -> None:
        if item_type not in self._supported_types:
            raise ValueError(
                f"JikanResultCache does not implement cache of type {item_type}."
            )


def _calculate_cache_key(item: str) -> str:
    try:
        key = hashlib.sha256(item.encode()).hexdigest()
    except AttributeError:
        if isinstance(item, int):
            key = item
        else:
            raise
    return key
