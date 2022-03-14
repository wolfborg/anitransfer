"""Implementations of caches."""

# default imports
import csv
import datetime
import json
import hashlib
import logging
import operator
import os
from typing import Any, Dict, Optional, List

# 3rd party imports
from appdirs import user_cache_dir
from dateutil.parser import parse
from .utils import format_log


class Blacklist:
    """Implement a list of items that cannot be mapped from anime-planet.com to myanimelist.net."""

    cache = []  # type: List[List[str]]
    cache_file = ""

    def __init__(self, blacklist_file: str) -> None:
        """Create a new Blacklist."""
        self.cache_file = blacklist_file

    def __enter__(self) -> "Blacklist":
        """Context manager for Blacklist to simplify cache load."""
        with open(self.cache_file, encoding='utf-8', mode='r') as cache:
            reader = csv.reader(cache)
            self.cache = list(reader)
        return self

    def __exit__(self, exception_type: Any, exception_value: Any, traceback: Any) -> None:
        """Context manager for Blacklist to simplify cache save."""
        with open(self.cache_file, encoding='utf-8', mode='w') as cache:
            writer = csv.writer(cache, quoting=csv.QUOTE_ALL)
            writer.writerows(sorted(self.cache))

    def add(self, name: str) -> None:
        """Add a title to the blacklist."""

    def lookup(self, name: str) -> bool:
        """Check if a title is blacklisted."""
        for title in self.cache:
            entry = format_log({"name": name})

            if title[0] == name:
                logging.info("Blacklist found: %s", entry)
                return True
        return False


class MappingCache:
    """Implement a mapping of anime-planet.com anime title to myanimelist.net ID."""

    def __init__(self, cache_file: str) -> None:
        """Create a new MappingCache."""
        self.cache_file = cache_file

    def add(self, name: str, myanimelist_id: str) -> None:
        """Add a mapping pair to the cache."""
        with open(self.cache_file, "r", encoding="utf-8") as before:
            cache = csv.reader(before)
            content = list(cache)
            content.append([name, myanimelist_id])
            content = sorted(content, key=operator.itemgetter(0))

        with open(self.cache_file, "w", encoding="utf-8") as after:
            writer = csv.writer(after, quoting=csv.QUOTE_ALL)
            writer.writerows(content)

        entry = format_log({"name": name, "myanimelist_id": myanimelist_id})
        logging.info("MappingCache added: %s", entry)

    def lookup(self, name: str) -> Optional[str]:
        """Look for a title in the cache."""
        with open(self.cache_file, "r", encoding="utf-8") as cache:
            reader = csv.reader(cache)
            data = list(reader)

        mapping = {}  # type: Dict[str, str]
        for row in data:
            mapping.update({row[0]: row[1]})

        if name in mapping:
            myanimelist_id = mapping[name]
            entry = format_log({"name": name, "myanimelist_id": myanimelist_id})
            logging.info("MappingCache found: %s", entry)
            return myanimelist_id
        return None


class RequestCache:
    """Implement a hash-addressed cache for Jikan results.

    The cache uses hashes instead of strings because anime like
    to use funny unicode symbols in their name. We do not want
    those on our users' filesystems just in case they hit an
    edge-case.
    """

    location = ""
    _supported_types = ["anime_title", "anime_search"]

    def __init__(self, ignore_expiry: bool = True) -> None:
        """Create a new RequestCache."""
        self.location = os.path.join(user_cache_dir(), "anitransfer", "jikan_cache")
        self.ignore_expiry = ignore_expiry

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
        logging.info("JikanRequestCache: added: %s", entry)

    def lookup(self, name: str, item_type: str) -> Optional[Dict[str, Any]]:
        """Look for an unexpired entry in the cache."""
        self._verify_type_is_supported(item_type)
        key = _calculate_cache_key(name)
        cache_location = os.path.join(self.location, item_type)
        location = os.path.join(cache_location, f"{key}.json")

        try:
            with open(location, "r", encoding="utf8") as cache_entry:
                entry = json.load(cache_entry)  # type: Dict[str, Any]
                expiry_date = entry["headers"]["Expires"]
        # FileNotFoundError: there is no such cache entry
        # KeyError: there is no expiration date in the entry
        # both of those will cause a cache miss
        except (FileNotFoundError, KeyError):
            return None

        date = parse(expiry_date)
        now = datetime.datetime.now(datetime.timezone.utc)
        if now > date:
            if not self.ignore_expiry:
                message = format_log({
                    "name": name,
                    "item_type": item_type,
                    "key": key,
                    "expiry_date": expiry_date})
                logging.info("RequestCache: entry expired: %s", message)
                return None

        message = format_log({"name": name, "item_type": item_type, "key": key})
        logging.info("RequestCache: found: %s", message)
        return entry

    def _verify_type_is_supported(self, item_type: str) -> None:
        """Ensure the used cache is implemented."""
        if item_type not in self._supported_types:
            raise ValueError(
                f"RequestCache does not implement cache of type {item_type}."
            )


def _calculate_cache_key(item: str) -> str:
    """Return the cache key for an item.

    Strings are hashed.
    Integers are returned as is.
    """
    try:
        key = hashlib.sha256(item.encode()).hexdigest()
    except AttributeError:
        if isinstance(item, int):
            key = item
        else:
            raise
    return key
