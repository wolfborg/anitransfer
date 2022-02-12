#!/usr/bin/env python3
"""Convert an anime-planet.com export to MyAnimeList XML format."""

# TODO: implement rich logging handler instead of streamhandler
# TODO: re-enable and update manual matching

# default imports
import argparse
import datetime
import logging
import json
import sys
from typing import Any, Dict, Optional, List, Union

# 3rd party imports
from jikanpy import Jikan
from jikanpy.exceptions import APIException
from rich import print as rprint
from rich.prompt import Confirm
from rich.progress import track, Progress

# internal imports
from utils.caches import RequestCache, MappingCache, Blacklist
from utils.exporters import AnimeExporter
from utils.statistics import Statistics
from utils.utils import format_log, JikanDelay

DEFAULTS = {
    'jikan_attempts': 2,  # amount of search results to use for extended search
    'jikan_delay': 4,  # in seconds
    'log_file': f'logs/log_{datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")}.txt',
    'log_level': 'WARNING',
    'cache_file': 'cache.csv',
    'bad_file': 'bad.csv',
    'outfile': 'convert.xml',
    'skip_confirm': False,
    'limit': None,
}


def load_export(filename: str) -> Dict[str, Dict[Any, Any]]:
    """Import the JSON file exported from anime-planet.com."""
    with open(filename, encoding='utf-8', mode='r') as source_file:
        content: Dict[str, Dict[Any, Any]] = json.load(source_file)
    return content


# def optionsCheck(name, jdata):
#     options = []
#     for i in jdata['results']:
#         options.append(str(i['title']).lower())
#     if name.lower() in options:
#         return options.index(name.lower())
#     return False


def verify(
    name: str,
    client: Jikan,
    jdata: Dict[str, Any],
    delay: int,
    cache: RequestCache
) -> Optional[List[Union[str, int]]]:
    """Try to match the Jikan result with the title provided."""
    # honestly, this line is only here to silence mypy thinking the default
    # may actually be an object and non-convertable
    if isinstance(DEFAULTS['jikan_attempts'], int):
        max_range = DEFAULTS['jikan_attempts']

    # try the first N results
    for index in range(0, max_range):
        entry = jdata['results'][index]
        name_for_comparison = name.lower()
        if name_for_comparison == entry['title'].lower():
            return [entry['title'], index]

        message = format_log({'name': name, 'suggestion': entry['title']})
        logging.info('Trying to match: %s', message)

        cached_request = cache.lookup(entry['mal_id'], 'anime_title')
        if cached_request:
            result = cached_request
            Statistics().increment('jikan_requests_cached')
        else:
            JikanDelay().check(delay)
            result = client.anime(entry['mal_id'])
            cache.add(entry['mal_id'], 'anime_title', result)
            Statistics().increment('jikan_requests')

        # looking for English titles is obvious
        if result.get('title_english'):
            message = format_log({'name': name, 'suggestion': result['title_english']})
            logging.info('Trying to match: %s', message)
            if result['title_english'].lower() == name_for_comparison:
                return [entry['title'], index]

        # anime-planet.com was initially a German site, so also try that
        # ...but apparently jikanpy doesn't give you 'title_german'.
        elif result.get('title_german'):
            if result['title_german'].lower() == name_for_comparison:
                return [entry['title'], index]

        # try different alternative titles
        if result.get('title_synonyms'):
            alternatives = result['title_synonyms']
            for item in alternatives:
                message = format_log({'name': name, 'suggestion': item})
                logging.info('Trying to match: %s', message)
                if item.lower() == name_for_comparison:
                    return [entry['title'], index]

    logging.info('No results: %s', format_log({'name': name}))
    return None

    # found = optionsCheck(name, jdata)
    # if found:
    #     return [str(jdata['results'][found]['title']), found]

    # print('Initial title: ' + name)
    # print(f'Found title: {entry["title"]} ({entry["url"]})')

    # return verify1(name, entry['title'], jdata)


# def verify1(name, jname, jdata):
#     q1 = 'Is this correct? [y/n]: '

#     # skips the prompt if set
#     skip = parse_arguments().skip_confirm
#     if skip:
#         print(q1 + 'SKIP')
#         return False

#     v1 = input(q1)
#     if v1.strip().lower() == 'n':
#         options = []
#         for i in jdata['results']:
#             options.append(f"{i['title']}\n    ({i['url']})")
#         print()
#         print('Initial title: ' + name)
#         print('[OTHER OPTIONS]')
#         x = 1
#         for o in options:
#             print('[' + str(x) + '] ' + o)
#             if x >= 9:
#                 break
#             x = x+1
#         print('[0] None of these')
#         return verify2(options)
#     elif v1.strip().lower() == 'y': return [jname, 0]
#     else:
#         print('ERROR: Bad input. Asking again.')
#         return verify1(name, jname, jdata)
#     return False


# def verify2(options):
#     q2 = 'Enter number for correct choice: '
#     v2 = input(q2)
#     if v2.strip() == '0': return False
#     elif int(v2) != False:
#         # print('option selected: ' + options[int(v2)-1])
#         return [options[int(v2)-1], int(v2)-1]
#     else:
#         print('ERROR: Bad input. Asking again.')
#         return verify2(options)
#     return False


def search_anime(
    name: str,
    options: argparse.Namespace,
    cache: RequestCache,
    failures: Optional[List[Any]] = None
) -> Optional[List[str]]:
    """Look for an anime on myanimelist.net using the Jikan API."""
    if not failures:
        failures = []
    entry = format_log({'name': name})

    if len(name) < 3:
        logging.error('Title too short for search.')
        return None

    rname = name.replace('&', 'and')
    message = format_log({'name': rname})
    logging.info("Looking up: %s", message)

    client = Jikan()

    cached_request = cache.lookup(name, 'anime_search')
    if cached_request:
        jfile = cached_request
        Statistics().increment('jikan_requests_cached')
    else:
        # adhere to Jikan API terms
        JikanDelay().check(options.jikan_delay)
        jfile = client.search('anime', rname)
        cache.add(name, 'anime_search', jfile)
        Statistics().increment('jikan_requests_total')

    if not jfile['results']:
        logging.info("No search results for: %s", entry)
        return None

    jver = verify(name, client, jfile, options.jikan_delay, cache)

    if not jver:
        logging.info("Matching failed: %s", entry)
        return None

    mal_id = jfile['results'][jver[1]]['mal_id']
    title = jfile['results'][jver[1]]['title']
    log_object = format_log({
        'name': name,
        'mal_id': mal_id,
        'mal_title': title,
    })
    logging.info('Matched: %s', log_object)
    Statistics().increment('entries_matched_using_jikan')
    return [str(mal_id), title]


def parse_arguments() -> argparse.Namespace:
    """Parse given command line arguments."""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        '--jikan-delay',
        help='Delay between API requests to Jikan in seconds',
        default=DEFAULTS['jikan_delay'],
        type=int
    )
    parser.add_argument(
        '--log-file',
        help='Write log of operations to this file',
        default=DEFAULTS['log_file']
    )
    parser.add_argument(
        '--cache-file',
        help='Cache file to use for already downloaded anime mappings',
        default=DEFAULTS['cache_file']
    )
    parser.add_argument(
        '--bad-file',
        help='Cache file to use for incompatible anime mappings',
        default=DEFAULTS['bad_file']
    )
    parser.add_argument(
        '--skip-confirm',
        help='Skip any confirmation prompts that show up',
        default=DEFAULTS['skip_confirm'],
        action='store_true'
    )
    parser.add_argument(
        '--non-interactive',
        help='Do only automatic matching and avoid prompting user',
        action='store_true'
    )
    parser.add_argument(
        '--outfile',
        help='Export file to render the export to',
        default=DEFAULTS['outfile']
    )

    parser.add_argument(
        '--limit',
        help='Limits the number of entries to process',
        default=DEFAULTS['limit'],
        type=int
    )
    parser.add_argument(
        '--log-level',
        help='Level of detail to use in log output',
        default=DEFAULTS['log_level'],
        choices=[
            'CRITICAL',
            'ERROR',
            'WARNING',
            'INFO',
            'DEBUG',
        ]
    )
    parser.add_argument('anime_list')

    options = parser.parse_args()
    return options


def prepare_logging(log_level: str, log_file: str) -> logging.Logger:
    """Set up logging configuration."""
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # stderr output
    formatter = logging.Formatter("[%(levelname)s] %(message)s")
    stream_handler = logging.StreamHandler(stream=sys.stderr)
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(log_level)
    logger.addHandler(stream_handler)

    # file output
    # this is https://en.wikipedia.org/wiki/ISO_8601
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s: %(funcName)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    logger.addHandler(file_handler)

    logging.info('Logging enabled.')
    logging.debug('Debug logging enabled.')

    return logger


def auto_match_titles(
    anime_to_process: List[Dict[str, Optional[Union[str, int]]]],
    processed: Dict[str, List[str]],
    anime_to_process_manually: List[Dict[str, Optional[Union[str, int]]]],
    options: argparse.Namespace
) -> List[Dict[str, Optional[Union[str, int]]]]:
    """Match titles to myanimelist IDs based on their title and alternative titles."""
    with Progress() as progress:
        failures = []  # type: List[Dict[str, Optional[Union[str, int]]]]
        anime_to_process_manually = []
        if not processed:
            processed = {}
        progress.console.print(f'Will try to automatically assign {len(anime_to_process)} titles.')
        processing = progress.add_task('Retrieving info...', total=len(anime_to_process))

        mapping = MappingCache(options.cache_file)
        request_cache = RequestCache()

        for anime in anime_to_process:
            try:
                rprint(f'Looking up {anime["name"]}')
                mal = search_anime(
                    str(anime['name']),
                    options,
                    request_cache,
                    failures
                )

                if mal and isinstance(anime["name"], str):
                    processed.update({anime['name']: mal})
                    mapping.add(str(anime['name']), mal[0])
                else:
                    anime_to_process_manually.append(anime)

            except (ConnectionError, APIException) as exception:
                entry = json.dumps({
                    'name': anime['name'],
                    'status': 'failure',
                    'jikan_info': exception.error_json
                    }, ensure_ascii=False)
                logging.info("Failed to retrieve search results for: %s", entry)
                Statistics().increment('jikan_requests_failed')
                failures.append(anime)

            finally:
                progress.update(processing, advance=1)

    if failures:
        rprint("Retrying failures...")
        anime_to_process_manually = anime_to_process_manually +(
            auto_match_titles(failures, processed, anime_to_process_manually, options)
        )

    return anime_to_process_manually


def filter_anime(
    entry: Dict[str, Optional[Union[str, int]]],
    processed: Dict[str, List[str]],
    anime_to_process: List[Dict[str, Optional[Union[str, int]]]],
    options: argparse.Namespace
) -> None:

    if entry['name']:
        name = str(entry['name'])

    # check blacklist first
    with Blacklist(options.bad_file) as blacklist:
        if blacklist.lookup(name):
            Statistics().increment('entries_matched_using_blacklist')
            return

    # continue if there's a chache hit
    cached_title = MappingCache(options.cache_file).lookup(name)
    if cached_title:
        Statistics().increment('entries_matched_using_cache')
        processed.update({name: [cached_title, name]})
        return

    # remove unsupported entries before internet lookup to save time
    if entry['status']:
        if entry['status'] == "won't watch":
            Statistics().increment('entries_unsupported')
            return

    # append to list if no matches
    anime_to_process.append(entry)


def main() -> None:
    """Take an anime-planet.com export and transform it into a useable import for anilist.co."""
    options = parse_arguments()
    prepare_logging(options.log_level, options.log_file)
    data = load_export(options.anime_list)
    anime_to_process = []  # List[Dict[str, Optional[Union[str, int]]]]
    anime_to_process_manually = []  # type: List[Dict[str, Optional[Union[str, int]]]]
    failures = []  # type: List[Dict[str, Optional[Union[str, int]]]]
    processed = {}  # type: Dict[str, List[str]]

    count = 0

    for entry in track(data['entries'], description='Filtering anime...'):
        filter_anime(entry, processed, anime_to_process, options)
        # Use this for smaller tests
        if options.limit and count >= options.limit:
            break

        count = count + 1
        Statistics().increment('entries_processed')

    anime_to_process_manually = auto_match_titles(
        anime_to_process,
        processed,
        anime_to_process_manually,
        options=options
    )

    for anime in anime_to_process_manually:
        # TODO: process them properly with search results
        Statistics().increment('entries_unmatched')
        failures.append(anime)

    if anime_to_process_manually and not options.non_interactive:
        Confirm.ask(
            f"Start manually mapping {len(anime_to_process_manually)} entries?", default=True
        )
    else:
        rprint('Skipping manual matching in non-interactive mode.')

    exporter = AnimeExporter(data['user']['name'], options.cache_file)
    for anime in data['entries']:
        if anime['name'] in processed:
            if not exporter.add(anime):
                Statistics().increment('entries_unsupported')

    exporter.export(options.outfile)
    Statistics().print_summary()


if __name__ == "__main__":
    main()
