#!/usr/bin/env python3
"""Convert an anime-planet.com export to MyAnimeList XML format."""

from xml.dom import minidom
import xml.etree.cElementTree as ET
import argparse
import csv
import datetime
import json
import math
import time
import requests
import logging
from datetime import date
import sys, os
import pyperclip
from dotenv import load_dotenv


load_dotenv()

MAL_CLIENT_ID = os.getenv('MAL_CLIENT_ID')

DEFAULTS = {
    'jikan_delay': 4, # in seconds
    'log_file': f'logs/anitransfer_{datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")}.txt',
    'cache_file': 'cache.csv',
    'bad_file': 'bad.csv',
    'skip_confirm': False,
    'cache_only': False,
    'with_links': False,
    'limit': -1,
}

def parse_arguments():
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
        help='Skip any confirmation prompts that show up, still tries initial search for entries',
        default=DEFAULTS['skip_confirm'],
        action='store_true'
    )
    parser.add_argument(
        '--cache-only',
        help='Runs process without looking up new matches, only cache mappings used.',
        default=DEFAULTS['cache_only'],
        action='store_true'
    )
    parser.add_argument(
        '--with-links',
        help='Displays links to found MyAnimeList entries to help with manual confirmation.',
        default=DEFAULTS['with_links'],
        action='store_true'
    )
    parser.add_argument(
        '--limit',
        help='Limits the number of entries to process',
        default=DEFAULTS['limit'],
        type=int
    )
    parser.add_argument('anime_list')

    args = parser.parse_args()
    return args

args = parse_arguments()

def setupLogger(LOG_FILE_NAME = str(date.today())+".log"):
    """Sets up and returns a log file to be used during a script."""
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    consoleHandler = logging.StreamHandler(sys.stdout)
    fileHandler = logging.FileHandler(LOG_FILE_NAME)
    consoleHandler.setLevel(logging.DEBUG)
    fileHandler.setLevel(logging.WARNING)
    
    consoleFormatter = logging.Formatter('%(message)s')
    fileFormatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    consoleHandler.setFormatter(consoleFormatter)
    fileHandler.setFormatter(fileFormatter)

    logger.addHandler(consoleHandler)
    logger.addHandler(fileHandler)

    return logger

logger = setupLogger(args.log_file)

#Loads JSON file
def loadJSON(filename):
    f = open(filename)
    data = json.load(f)
    f.close()
    return data

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
            logger.info('Cached ID found: ' + name + ' ---> ' + mal)
            return mal
    #print('Cached Not found.')
    return False

def badSearch(name, bad_file):
    with open(bad_file, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        data = list(reader)

    for i in data:
        if i[0] == name:
            logger.info('Bad title found: ' + name + ' ---> SKIP')
            return True
    return False

qtime = datetime.datetime.now()

def delayCheck(delay):
    global qtime
    now = datetime.datetime.now()
    dtime = now - qtime
    secs = dtime.total_seconds()
    diff = math.ceil(delay - secs)
    if secs < delay:
        time.sleep(diff)
    qtime = datetime.datetime.now()

def optionsCheck(name, jdata):
    options = []
    for i in jdata['data']:
        options.append(str(i['title']).lower())
    if name.lower() in options:
        return options.index(name.lower())
    return False

def jverify(name, jdata):
    jname = str(jdata['data'][0]['title'])
    if name.lower() == jname.lower():
        return [jname, 0]

    found = optionsCheck(name, jdata)
    if found != False:
        return [str(jdata['data'][found]['title']), found]

    # print('Found title: ' + jname)

    return displayOptions(jdata)

def displayOptions(jdata):
    if args.skip_confirm:
        logger.info('SKIP: Skipping confirmation')
        return False

    numOptions = 10
    options = []
    for i in jdata['data']:
        options.append(str(i['title']))
    print()
    print('[OTHER OPTIONS]')
    x = 1
    for entry in jdata['data']:
        title = str(entry['title'])
        url = str(entry['url'])
        options.append(title)
        print('[' + str(x) + '] ' + title)
        if args.with_links:
            print(url)
            print()
        if x >= numOptions:
            break
        x = x+1
    print('[i] Manual ID')
    print('[n] Skip entry')
    return prompt(options, numOptions)

def prompt(options, numOptions):
    v2 = input('Enter number for correct choice: ')
    if v2.strip() == '' or v2.strip() == 'n':
        return False
    elif v2.strip() == 'i':
        malID = input("Enter MAL ID: ")
        return malID
    elif v2.isdigit() and int(v2) <= numOptions:
        return [options[int(v2)-1], int(v2)-1]
    
    logger.debug('ERROR: Bad input. Asking again.')
    return prompt(options, numOptions)

def malSearch(name):
    print()
    logger.info('Initial title: ' + name)
    pyperclip.copy(name)

    if len(name) < 3:
        logger.error("Search title too small - " + name)
        return False

    rname = name.replace('&','and')

    try:
        jikan = requests.get("https://api.jikan.moe/v4/anime?q="+rname)
        jfile = jikan.json()
    except:
        logger.error("Jikan request failed")
        return False

    jdata = json.loads(json.dumps(jfile))
    if len(jdata['data']) == 0:
        logger.error("Jikan search found no entries")
        return False

    jver = jverify(name, jdata)

    if jver == False:
        logger.error("Couldn't find - " + name)
        return False

    if isinstance(jver, str):
        return jver
    
    return [str(jdata['data'][jver[1]]['mal_id']), jver[0]]



def main():
    #Start MAL XML structure
    root = ET.Element('myanimelist')
    info = ET.SubElement(root, 'myinfo')
    uname = ET.SubElement(info, 'user_name')
    total = ET.SubElement(info, 'user_total_anime')

    data = loadJSON(args.anime_list)
    uname.text = data['user']['name']

    count = 0
    cacheFound = 0
    searchFound = 0
    notFound = 0
    for i in data['entries']:
        #Use this for smaller tests
        limit = args.limit
        if limit > -1 and count >= limit:
            break

        cached = False
        count = count + 1

        name = i['name']
        if badSearch(name, args.bad_file):
            logger.error("Couldn't find - " + name)
            continue

        entryid = cacheSearch(name, args.cache_file)
        if entryid == False:
            if args.cache_only:
                logger.info('CACHE ONLY: Skipping Jikan search')
                notFound += 1
                logger.error("Couldn't find - " + name)
                continue
            
            print('==============')
            mal = malSearch(name)
            if mal == False:
                delayCheck(args.jikan_delay)
                notFound += 1
                continue
            else:
                if isinstance(mal, str) == False:
                    mal = mal[0]
                cache(i['name'], mal, args.cache_file)
                entryid = mal
                searchFound += 1
        else:
            cached = True
            cacheFound += 1

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

        malid.text = entryid
        title.text = name
        status.text = stat
        weps.text = str(i['eps'])

        wsd.text = "0000-00-00"
        wfd.text = "0000-00-00"
        score.text = str(int(i['rating']*2))
        twatched.text = "0"

        if str(i['started']) != "None": 
            wsd.text = str(i['started']).split()[0]
        
        if str(i['completed']) != "None":
            wfd.text = str(i['completed']).split()[0]

        # becomes num of rewatches on MAL, so subtract 1
        if (i['times'] > 1):
            twatched.text = str(i['times']-1)

        #MUST use 4 second delay for Jikan's rate limit
        if cached == False:
            name = i['name']
            jname = mal[1]
            strlog = str(count) + ": " + name + " ---> " + jname
            logger.info("Adding to cache: "+strlog)
            delayCheck(args.jikan_delay)

    total.text = str(cacheFound + searchFound)

    #Export XML to convert file
    #tree = ET.ElementTree(root)
    dom = minidom.parseString(ET.tostring(root))
    dom = dom.toprettyxml(indent='\t')
    with open('convert.xml', 'w', encoding='utf-8') as f2:
        f2.write(dom)

    print("=================================")
    logger.info("Total Entries: "+str(len(data['entries'])))
    logger.info("Cache Found: "+str(cacheFound))
    logger.info("Search Found: "+str(searchFound))
    logger.info("Not Found: "+str(notFound))


if __name__ == "__main__":
    main()
