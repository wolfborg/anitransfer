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
import webbrowser
from dotenv import load_dotenv
import urllib.parse

sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

MAL_CLIENT_ID = os.getenv('MAL_CLIENT_ID')

current_datetime = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S");

DEFAULTS = {
    'api_delay': 1.5, # in seconds
    'log_file': 'logs/anitransfer_'+current_datetime+'.txt',
    'cache_file': 'cache.csv',
    'bad_file': 'bad.csv',
    'skip_confirm': False,
    'cache_only': False,
    'with_links': False,
    'mal_api': False,
    'num_options': 10,
    'limit': -1,
}

def parse_arguments():
    """Parse given command line arguments."""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        '--api-delay',
        help='Delay between API requests in seconds',
        default=DEFAULTS['api_delay'],
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
        '--mal-api',
        help='Uses MAL API instead when doing search (MAL_CLIENT_ID  required in .env file).',
        default=DEFAULTS['mal_api'],
        action='store_true'
    )
    parser.add_argument(
        '--limit',
        help='Limits the number of entries to process',
        default=DEFAULTS['limit'],
        type=int
    )
    parser.add_argument(
        '--num-options',
        help='Determines the max number of options to display during options select.',
        default=DEFAULTS['num_options'],
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
    fileHandler = logging.FileHandler(filename=LOG_FILE_NAME, mode='w', encoding='utf-8')
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
    f = open(filename, encoding='utf-8')
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

def bad(name, bad_file):
    with open(bad_file, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow([name])

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

def jikanGetTitles(entry):
    titles = [entry['title']]
    if 'title_english' in entry and entry['title_english'] != None:
        titles.append(entry['title_english'])
    if 'titles' in entry:
        altTitles = entry['titles']
        for altTitle in altTitles:
            if altTitle['type'] == 'English':
                titles.append(altTitle['title'])
    if 'title_synonyms' in entry:
        for synonyms in entry['title_synonyms']:
            titles.append(synonyms)
    return titles

def jikanSearch(name):
    try:
        query = urllib.parse.quote_plus(str(name))
        url = "https://api.jikan.moe/v4/anime?q="+query
        jikan = requests.get(url)
        if jikan.status_code == 400:
            logger.error("Jikan 400 -- "+name)
            return False
        jfile = jikan.json()
    except:
        logger.error("Jikan request failed -- "+name)
        return False

    jikanData = json.loads(json.dumps(jfile))
    if len(jikanData['data']) == 0:
        logger.error("Jikan search found no entries -- "+name)
        return False
    
    jikanOptions = []
    jikanEntries = jikanData['data']
    for entry in jikanEntries:
        id = str(entry['mal_id'])
        link = "https://myanimelist.net/anime/"+id

        titles = jikanGetTitles(entry)
        if name.lower() in [x.lower() for x in titles]:
            logger.info("Jikan match found: "+id)
            return id

        jikanOption = {"id": id, "titles": titles, "link": link}
        jikanOptions.append(jikanOption)
    
    selection = optionSelect(jikanOptions)
    if selection == False:
        logger.error("Couldn't find title -- "+name)
        return False
    return selection

def malGetTitles(entry):
    titles = [entry['title']]
    altTitles = entry['alternative_titles']
    if 'en' in altTitles:
        titles.append(altTitles['en'])
    if 'synonyms' in altTitles:
        for synonyms in altTitles['synonyms']:
            titles.append(synonyms)
    return titles

def malSearch(full_name, assume_match=True):
    name = full_name

    if len(name) >= 65:
        name = name[:64]
        logger.info("Search title too long, shortening: -- " + name)
        assume_match = False

    try:
        headers = {'X-MAL-CLIENT-ID': MAL_CLIENT_ID}
        query = urllib.parse.quote_plus(str(name))
        url = "https://api.myanimelist.net/v2/anime?q="+query
        fields = "id,title,alternative_titles,start_date,end_date,media_type,num_episodes,start_season,source,average_episode_duration,studios"
        url += "&fields="+fields+"&nsfw=true"
        mal = requests.get(url, headers=headers)
        if mal.status_code == 400:
            logger.error("MAL 400 -- "+name)
            return False
        malFile = mal.json()
    except:
        logger.error("MAL request failed -- "+name)
        return False

    malData = json.loads(json.dumps(malFile))
    if len(malData['data']) == 0:
        logger.error("MAL search found no entries -- "+name)
        return False

    malOptions = []
    malEntries = malData['data']
    for entry in malEntries:
        entry = entry['node']
        id = str(entry['id'])
        link = "https://myanimelist.net/anime/"+id
 
        titles = malGetTitles(entry)
        if assume_match:
            if name.lower() in [x.lower() for x in titles]:
                logger.info("MAL match found: "+id)
                return id

        malOption = {"id": id, "titles": titles, "link": link}
        malOptions.append(malOption)
    
    selection = optionSelect(malOptions, full_name)
    if selection == False:
        logger.error("Couldn't find title -- "+ full_name)
        return False
    return selection

def printOptionInfo(id, titles, link):
    print("MAL ID: "+id)
    for title in titles:
        print(" - "+title)
    if args.with_links:
        print(link)
    print()

def prompt(options, numOptions, name):
    answer = input('Enter number for correct choice: ')
    if answer.strip() == '':
        return False
    elif answer.strip() == 'i':
        malID = input("Enter MAL ID: ")
        return malID
    elif answer.strip() == 'b':
        bad(name, args.bad_file)
        return False
    elif answer.isdigit() and int(answer) <= numOptions:
        answer = int(answer)-1
        return options[answer]['id']
    logger.debug('ERROR: Bad input. Asking again.')
    return prompt(options, numOptions, name)

def optionSelect(options, name):
    if args.skip_confirm:
        logger.info('SKIP: Skipping confirmation')
        return False

    numOptions = args.num_options
    print()
    print('[OPTIONS]')
    x = 1
    for option in options:
        title = option['titles'][0]
        link = option['link']
        print('[' + str(x) + '] ' + title)
        # printOptionInfo(id, titles, link)
        if args.with_links:
            print(link)
            print()
        if x >= numOptions:
            break
        x = x+1
    print('[i] Manual ID')
    print('[b] Mark as bad entry')
    print('[ENTER] Skip entry')
    getConfirmInfo(name)
    return prompt(options, numOptions, name)

def search(name):
    print()
    print('==============')
    logger.info('Anime Planet title: ' + name)

    if len(name) < 3:
        logger.error("Search title too small -- " + name)
        return False

    if args.mal_api:
        malResult = malSearch(name)
        print('==============')
        print()
        if malResult:
            return malResult
        return False

    jikanResult = jikanSearch(name)

    print('==============')
    print()
    if jikanResult:
        return jikanResult
    return False

def getConfirmInfo(name):
    #pyperclip.copy(name)
    query = urllib.parse.quote_plus(str(name))
    mal_url = "https://myanimelist.net/anime.php?cat=anime&q="+query[:99]
    webbrowser.open(mal_url, new=2, autoraise=True)
    planet_url = "https://www.anime-planet.com/anime/all?name="+query
    webbrowser.open(planet_url, new=2, autoraise=True)


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
    badFound = 0
    searchFound = 0
    notFound = 0

    for i in data['entries']:
        #Use this for smaller tests
        limit = args.limit
        if limit > -1 and count >= limit:
            break

        cached = False
        count += 1

        name = i['name']
        if badSearch(name, args.bad_file):
            logger.error("Bad title -- "+name)
            badFound += 1
            continue

        foundID = cacheSearch(name, args.cache_file)
        if foundID == False:
            if args.cache_only:
                logger.info('CACHE ONLY: Skipping search')
                notFound += 1
                logger.error("Couldn't find title -- "+name)
                continue
            
            foundID = search(name)
            if foundID == False:
                notFound += 1
                delayCheck(args.api_delay)
                continue
            else:
                searchFound += 1
                cache(name, foundID, args.cache_file)
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

        malid.text = foundID
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

        #MUST use 4 second delay for API rate limits
        if cached == False:
            strlog = str(count) + ": " + name + " ---> " + foundID
            logger.info("Adding to cache: "+strlog)
            delayCheck(args.api_delay)

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
    logger.info("Bad Found: "+str(badFound))
    logger.info("Search Found: "+str(searchFound))
    logger.info("Not Found: "+str(notFound))


if __name__ == "__main__":
    main()
