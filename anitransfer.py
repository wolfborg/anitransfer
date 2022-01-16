#!/usr/bin/env python3
"""Convert an anime-planet.com export to MyAnimeList XML format."""

from typing import Any, Dict
from xml.dom import minidom
import xml.etree.cElementTree as ET
import argparse
import csv
import datetime
import logging
import json
import math
import time
import sys

from jikanpy import Jikan

DEFAULTS = {
    'jikan_delay': 4, # in seconds
    'log_file': f'logs/log_{datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")}.txt',
    'log_level': 'WARNING',
    'cache_file': 'cache.csv',
    'bad_file': 'bad.csv',
    'skip_confirm': False,
    'limit': -1,
}

qtime = datetime.datetime.now()

def load_export(filename: str) -> Dict[str, Dict[Any, Any]]:
    """Import the JSON file exported from anime-planet.com."""
    with open(filename, encoding='utf-8', mode='r') as source_file:
        content: Dict[str, Dict[Any, Any]] = json.load(source_file)
    return content

#Prints logs and errors and appends to log file
def log(type, name, jname=None, count=0):
    logfile = parse_arguments().log_file

    if type == 1: strlog = "ERROR: Search title too small - " + name
    elif type == 2: strlog = "ERROR: Couldn't find - " + name
    elif type == 3: strlog = "ERROR: Duplicate - " + name + " ---> " + jname
    else: strlog = str(count) + ": " + name + " ---> " + jname

    if type == 1 or type == 2 or type == 3:
        with open(logfile, 'a', encoding='utf-8') as f:
            f.write(strlog + '\n')
    print(strlog)

def cache(name, malid, cache_file):
    with open(cache_file, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow([name, malid])

def cacheSearch(name, cache_file):
    with open(cache_file, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        data = list(reader)

    for i in data:
        if i[0] == name:
            mal = i[1]
            print('Cached ID found: ' + name + ' ---> ' + mal)
            return mal
    #print('Cached Not found.')
    return False

def badSearch(name, bad_file):
    with open(bad_file, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        data = list(reader)

    for i in data:
        if i[0] == name:
            print('Bad title found: ' + name + ' ---> ERROR')
            return True
    return False

def delayCheck(delay):
    global qtime
    now = datetime.datetime.now()
    dtime = now - qtime
    secs = dtime.total_seconds()
    diff = math.ceil(delay - secs)
    #print('TIME DELAY: ' + str(diff))
    if secs < delay:
        time.sleep(diff)
    qtime = datetime.datetime.now()

def optionsCheck(name, jdata):
    options = []
    for i in jdata['results']:
        options.append(str(i['title']).lower())
    if name.lower() in options:
        return options.index(name.lower())
    return False

def jverify(name, jdata):
    jname = str(jdata['results'][0]['title'])
    if name.lower() == jname.lower():
        return [jname, 0]

    found = optionsCheck(name, jdata)
    if found != False:
        return [str(jdata['results'][found]['title']), found]

    print('Found title: ' + jname)

    return verify1(name, jname, jdata)

def verify1(name, jname, jdata):
    q1 = 'Is this correct? [y/n]: '

    #skips the prompt if set
    skip = parse_arguments().skip_confirm
    if skip:
        print(q1 + 'SKIP')
        return False

    v1 = input(q1)
    if v1.strip().lower() == 'n':
        options = []
        for i in jdata['results']:
            options.append(str(i['title']))
        print()
        print('Initial title: ' + name)
        print('[OTHER OPTIONS]')
        x = 1
        for o in options:
            print('[' + str(x) + '] ' + o)
            if x >= 9:
                break
            x = x+1
        print('[0] None of these')
        return verify2(options)
    elif v1.strip().lower() == 'y': return [jname, 0]
    else:
        print('ERROR: Bad input. Asking again.')
        return verify1(name, jname, jdata)
    return False

def verify2(options):
    q2 = 'Enter number for correct choice: '
    v2 = input(q2)
    if v2.strip() == '0': return False
    elif int(v2) != False:
        #print('option selected: ' + options[int(v2)-1])
        return [options[int(v2)-1], int(v2)-1]
    else:
        print('ERROR: Bad input. Asking again.')
        return verify2(options)
    return False

def malSearch(name):
    print()
    print('Initial title: ' + name)

    #Initiate Jikan
    jikan = Jikan()

    if len(name) < 3:
        log(1, name)
        return False

    rname = name.replace('&','and')

    try:
        jfile = jikan.search('anime', rname)
    except:
        log(2, name)
        return False

    jdata = json.loads(json.dumps(jfile))
    jver = jverify(name, jdata)

    if jver == False:
        log(2, name)
        return False

    return [str(jdata['results'][jver[1]]['mal_id']), jver[0]]

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
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)

    logging.info('Logging enabled.')
    logging.debug('Debug logging enabled.')

    return logger


def print_summary(statistics: Dict[str,int]) -> None:
    """Print a usage summary at the end of a run."""

    formatted = f"""Summary:
    Processed {statistics['processed']} entries.
    Excluded {statistics['blacklisted']} entries based on blacklist.
    Found {statistics['cached']} entries using local cache.
    Used {statistics['requests']} requests to Jikan to assign {statistics['assigned']} titles."""

    print(formatted)

def increment(statistics: Dict[str,int], value: str) -> None:
    """Add an entry to the relevant key of the usage statistics."""
    statistics.update({value: statistics[value] + 1})

def main() -> None:
    # Make log and load data
    options = parse_arguments()
    createLog(options.log_file)
    data = load_export(options.anime_list)

    statistics = {
        'assigned': 0, # amount of new entries that were assigned using Jikan
        'blacklisted': 0, # amount of entries that match a blacklist entry
        'cached': 0, # amount of entries that match a cache entry
        'processed': 0, # amount of total entries processed
        'requests': 0, # amount of total API requests to Jikan
    }

    #Start XML structure
    root = ET.Element('myanimelist')
    info = ET.SubElement(root, 'myinfo')
    uname = ET.SubElement(info, 'user_name')
    total = ET.SubElement(info, 'user_total_anime')
    uname.text = data['user']['name']
    total.text = str(len(data['entries']))

    count = 0

    for i in data['entries']:
        #Use this for smaller tests
        limit = options.limit
        if limit > -1:
            if count >= limit:
                break

        cached = False
        count = count + 1

        name = i['name']
        if badSearch(name, options.bad_file):
            log(2, name)
            continue

        mal = cacheSearch(name, options.cache_file)
        if mal == False:
            mal = malSearch(name)
            if mal == False:
                delayCheck(options.jikan_delay)
                continue
            else: cache(i['name'], mal[0], options.cache_file)
        else:
            cached = True
            increment(statistics, 'cached')

        #Convert status
        stat = i['status']
        if stat == 'watched': stat = 'Completed'
        elif stat == 'watching': stat = 'Watching'
        elif stat == 'want to watch': stat = 'Plan to Watch'
        elif stat == 'stalled': stat = 'On-Hold'
        elif stat == 'dropped': stat = 'Dropped'
        elif stat == "won't watch": continue

        #Populate anime XML entry
        entry = ET.SubElement(root, 'anime')
        malid = ET.SubElement(entry, 'series_animedb_id')
        title = ET.SubElement(entry, 'series_title')
        weps = ET.SubElement(entry, 'my_watched_episodes')
        wsd = ET.SubElement(entry, 'my_start_date')
        wfd = ET.SubElement(entry, 'my_finish_date')
        score = ET.SubElement(entry, 'my_score')
        status = ET.SubElement(entry, 'my_status')
        twatched = ET.SubElement(entry, 'my_times_watched')

        if cached == False:
            malid.text = mal[0]
        else:
            malid.text = mal

        title.text = name
        status.text = stat
        weps.text = str(i['eps'])
        if str(i['started']) == "None": wsd.text = "0000-00-00"
        else: wsd.text = str(i['started']).split()[0]
        if str(i['completed']) == "None": wfd.text = "0000-00-00"
        else: wfd.text = str(i['completed']).split()[0]
        score.text = str(int(i['rating']*2))
        if (i['times'] > 1): twatched.text = str(i['times']-1)
        else: twatched.text = "0"

        #MUST use 4 second delay for Jikan's rate limit
        if cached == False:
            log(0, i['name'], mal[1], count)
            delayCheck(options.jikan_delay)

    #Export XML to convert file
    tree = ET.ElementTree(root)
    dom = minidom.parseString(ET.tostring(root))
    dom = dom.toprettyxml(indent='\t')
    with open('convert.xml', 'w', encoding='utf-8') as f2:
        f2.write(dom)

    print_summary(statistics)

if __name__ == "__main__":
    main()
