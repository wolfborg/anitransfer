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
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service

start_time = datetime.datetime.now()
start_datetime = start_time.strftime("%Y-%m-%d_%H%M%S")
qtime = datetime.datetime.now()
sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()
MAL_CLIENT_ID = os.getenv('MAL_CLIENT_ID')

DEFAULTS = {
    'api_delay': 1.5, # in seconds
    'log_file': 'logs/anitransfer/anitransfer_'+start_datetime+'.txt',
    'cache_file': 'mappings/anime_cache.csv',
    'bad_file': 'mappings/anime_bad.csv',
    'unmapped_file': 'mappings/anime_unmapped.csv',
    'skip_confirm': False,
    'cache_only': False,
    'with_mal_links': False,
    'with_mal_info': False,
    'open_tabs': False,
    'mal_api': False,
    'selenium': False,
    'num_options': 10,
    'search_queue': False,
    'anime_list': 'export-anime.json',
    'limit': -1,
    'offset': 0,
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
        '--unmapped-file',
        help='Cache file to use for anime mappings that have not been reviewed yet',
        default=DEFAULTS['unmapped_file']
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
        '--with-mal-links',
        help='Displays links to found MyAnimeList entries to help with manual confirmation.',
        default=DEFAULTS['with_mal_links'],
        action='store_true'
    )
    parser.add_argument(
        '--with-mal-info',
        help='Displays entry info for found MyAnimeList entries to help with manual confirmation.',
        default=DEFAULTS['with_mal_info'],
        action='store_true'
    )
    parser.add_argument(
        '--selenium',
        help='Launches a selenium web browser, required for automatically checking Anime Planet info.',
        default=DEFAULTS['selenium'],
        action='store_true'
    )
    parser.add_argument(
        '--open-tabs',
        help='Opens the Anime Planet and MyAnimeList search tabs in your browser during manual confirmation',
        default=DEFAULTS['open_tabs'],
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
        '--offset',
        help='Determines which entry number to start with during search queue processing',
        default=DEFAULTS['offset'],
        type=int
    )
    parser.add_argument(
        '--num-options',
        help='Determines the max number of options to display during options select.',
        default=DEFAULTS['num_options'],
        type=int
    )
    parser.add_argument(
        '--search-queue',
        help='Ignores all list processing, simply begins searches to clear the unmapped queue.',
        default=DEFAULTS['search_queue'],
        action='store_true'
    )
    parser.add_argument(
        '--anime-list',
        help='Anime Planet JSON export file to process. Not needed when using --search-queue.',
        default=DEFAULTS['anime_list']
    )

    args = parser.parse_args()
    return args

args = parse_arguments()

if args.selenium:
    service = Service(executable_path="chromedriver.exe")
    driver = webdriver.Chrome(service=service)

def processCacheFiles(file):
    with open(file, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        data = list(reader)
        
    return data

cache_data = processCacheFiles(args.cache_file)
bad_data = processCacheFiles(args.bad_file)
#unmapped_data = processCacheFiles(args.unmapped_file)

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

def cache(name, malid):
    with open(args.cache_file, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow([name, malid])

def cacheSearch(name):
    for i in cache_data:
        if i[0] == name:
            mal = i[1]
            #logger.info('Cached ID found: ' + name + ' ---> ' + mal)
            return mal
    #print('Cached Not found.')
    return False

def badSearch(name):
    for i in bad_data:
        if i[0] == name:
            #logger.info('Bad title found: ' + name + ' ---> SKIP')
            return True
    return False

def bad(name):
    with open(args.bad_file, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow([name])

def delayCheck(delay):
    global qtime
    now = datetime.datetime.now()
    dtime = now - qtime
    secs = dtime.total_seconds()
    #diff = math.ceil(delay - secs)
    diff = delay - secs
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
    
    selection = optionSelect(jikanOptions, name)

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

def malSearch(full_name, anime_planet_info=False, assume_match=True):
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
    #print(malData['data'][0])
    for entry in malEntries:
        entry = entry['node']
        id = str(entry['id'])
        link = "https://myanimelist.net/anime/"+id
        
        start_year = "Unknown"
        if "start_date" in entry:
            start_year = str(entry['start_date'].split('-')[0])
        num_eps = str(entry['num_episodes'])
        ep_length = str(round(entry['average_episode_duration'] / 60))
        media_type = str(entry['media_type'])

        studio = ""
        if len(entry['studios']) > 0:
            studio = str(entry['studios'][0]['name'])
 
        titles = malGetTitles(entry)
        if assume_match:
            if name.lower() in [x.lower() for x in titles]:
                logger.info("MAL match found: "+id)
                logger.info("MAL title: "+titles[0])
                return id

        if anime_planet_info:
            ap_start_year = anime_planet_info['start_year']
            ap_num_eps = anime_planet_info['num_eps']
            ap_ep_length = anime_planet_info['ep_length']
            ap_media_type = anime_planet_info['media_type']
            ap_studio = anime_planet_info['studio']

            if start_year == ap_start_year and num_eps == ap_num_eps and studio == ap_studio:
                logger.info("MAL match found: "+id)
                logger.info("MAL title: "+titles[0])
                return id

        malOption = {
            "id": id,
            "titles": titles,
            "link": link,
            "start_year": start_year,
            "num_eps": num_eps,
            "ep_length": ep_length,
            "studio": studio,
            "media_type": media_type
        }
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
    if args.with_mal_links:
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
        bad(name)
        removeUnmapped(name)
        return False
    elif answer.strip() == 'q':
        return -1
    elif answer.isdigit() and int(answer) <= numOptions:
        answer = int(answer)-1
        return options[answer]['id']
    
    logger.debug('ERROR: Bad input. Asking again.')
    return prompt(options, numOptions, name)

def optionSelect(options, name):
    if args.skip_confirm:
        print()
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
        
        if args.mal_api and args.with_mal_info:
            num_eps = option['num_eps']
            start_year = option['start_year']
            ep_length = option['ep_length']
            media_type = option['media_type']
            studio = option['studio']

            print(start_year + " -- " + num_eps + " ep -- " + ep_length + " mins -- " + studio + " -- " + media_type)

        if args.with_mal_links:
            print(link)
            print()
        if x >= numOptions:
            break
        x = x+1
    
    print()
    print('[i] Enter manual ID')
    print('[b] Mark as bad entry')
    print('[q] Quit program')
    print('[ENTER] Skip entry')

    if args.open_tabs:
        openTabs(name)

    return prompt(options, numOptions, name)

def search(name):
    print()
    print('==============')
    print('[ANIME PLANET]')
    print('[*] '+ name)

    if len(name) < 3:
        logger.error("Search title too small -- " + name)
        return False

    if args.skip_confirm:
        delayCheck(args.api_delay)

    anime_planet_info = False

    if args.selenium:
        anime_planet_info = getAnimePlanetInfo(name)

    if args.mal_api:
        malResult = malSearch(name, anime_planet_info)
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

def getAnimePlanetInfo(name):
    anime_planet_info = {}

    query = urllib.parse.quote_plus(str(name))

    anime_planet_domain = "https://www.anime-planet.com"
    anime_planet_query_url = anime_planet_domain + "/anime/all?name="+query

    global driver
    driver.get(anime_planet_query_url)

    if args.skip_confirm:
        time.sleep(1)

    #driver.get("https://www.anime-planet.com/anime/all?name=test")

    if (anime_planet_domain + "/anime/all?name=") in driver.current_url:
        soup = BeautifulSoup(driver.page_source, "html.parser")
        cards = soup.find_all("li", {"class": "card"})

        anime_planet_found = False
        for card in cards:
            title = card.find("h3", {"class": "cardName"}).text
            link = anime_planet_domain + card.find("a")['href']
            if title == name:
                anime_planet_found = True
                driver.get(link)

        if anime_planet_found == False:
            logger.error("Unable to automatically find Anime Planet url for title: " + str(name))
            return anime_planet_info
    
    content = driver.page_source
    soup = BeautifulSoup(content, "html.parser")

    info_section = soup.find("section", {"class": "pure-g entryBar"})

    start_year = "???"
    num_eps = "???"
    ep_length = "???"
    studio = "???"
    media_type = "???"


    start_year = info_section.find("span", {"class": "iconYear"}).text.strip().split(" - ")[0]

    ep_info = info_section.find("span", {"class": "type"}).text
    if " ep" in ep_info:
        ep_info_split = ep_info.split("(")
        if len(ep_info_split) > 1:
            ep_info = ep_info_split[1].replace(")","").strip()

        num_eps = ep_info.split(" ep")[0].strip()
        if "+" in num_eps:
            num_eps = "???"

        ep_length_splitter = " eps x "
        if num_eps != "???" and int(num_eps) == 1:
            ep_length_splitter = " ep x "

        ep_length_split = ep_info.split(ep_length_splitter)
        if len(ep_length_split) > 1:
            ep_length = ep_length_split[1].replace(" min", "").strip()

    studio_html = info_section.find("a")
    if studio_html:
        studio = studio_html.text.strip()
    
    media_type = info_section.find("span", {"class": "type"}).text.split("(")[0].strip().lower()

    #print("start_year:" + str(start_year))
    #print("num_eps: " + str(num_eps))
    #print("ep_length: " + str(ep_length))
    #print("studio: " + str(studio))
    #print("media_type: " + str(media_type))

    print(start_year + " -- " + num_eps + " ep -- " + ep_length + " mins -- " + studio + " -- " + media_type)

    anime_planet_info = {
        "start_year": start_year,
        "num_eps": num_eps,
        "ep_length": ep_length,
        "studio": studio,
        "media_type": media_type
    }

    return anime_planet_info


def openTabs(name):
    #pyperclip.copy(name)
    query = urllib.parse.quote_plus(str(name))
    #mal_url = "https://myanimelist.net/anime.php?cat=anime&q="+query[:99]
    #webbrowser.open(mal_url, new=2, autoraise=True)
    anime_planet_url = "https://www.anime-planet.com/anime/all?name="+query
    webbrowser.open(anime_planet_url, new=2, autoraise=True)

def getInitialCounts(data, root):
    cacheFound = 0
    badFound = 0
    notFound = 0

    cachedEntries = []
    notFoundEntries = []
    badEntries = []

    for entry in data['entries']:
        name = entry['name']
        
        if badSearch(name):
            badFound += 1
            badEntries.append(entry)
            logger.error("Bad title -- "+name)
            logger.info('Bad title found: ' + name + ' ---> SKIP')
            continue

        foundID = cacheSearch(name)
        if foundID != False:
            cacheFound += 1
            cachedEntries.append(entry)
            logger.info('Cached ID found: ' + name + ' ---> ' + foundID)
            
            convertEntry(entry, foundID, root)
            continue
        
        notFound += 1
        notFoundEntries.append(entry)
        
        unmappedEntry = unmappedCheck(name, args.unmapped_file)
        if unmappedEntry == False:
            unmapped(name, args.unmapped_file)
    
    print("=================================")
    print("Total Entries: "+str(len(data['entries'])))
    print("Cache Found: "+str(cacheFound))
    print("Bad Found: "+str(badFound))
    print("Not Found: "+str(notFound))

    return (cachedEntries, notFoundEntries, badEntries)

def searchEntries(entries, root):
    count = 0
    found = 0
    notFound = 0

    #queueTotal = len(entries)

    foundEntries = []
    notFoundEntries = []
    
    for entry in entries:
        if count < args.offset:
            count += 1
            continue

        #Use this for smaller tests
        limit = args.limit
        if limit > -1 and count >= limit:
            break

        foundID = False
        count += 1
        
        name = entry['name']
        foundID = search(name)

        if foundID == -1:
            logger.info("Quitting program...")
            break

        if foundID == False:
            notFound += 1
            notFoundEntries.append(entry)
            #unmapped(name, args.unmapped_file)
            #MUST use 4 second delay for Jikan API rate limits
            #delayCheck(args.api_delay)
            continue

        found += 1

        foundEntries.append(foundID)
        cache(name, foundID)

        convertEntry(entry, foundID, root)

        strlog = str(count) + ": " + name + " ---> " + foundID
        logger.info("Added to cache: "+strlog)

        #MUST use 4 second delay for Jikan API rate limits
        #delayCheck(args.api_delay)

    return foundEntries

def processConfirm():
    if args.skip_confirm:
        print("There is a search queue. Please use --search-queue to process the remaining unconfirmed entries. When the search queue is clear you can use --cache-only to generate your converted list.")
        return False

    answer = input("There is a search queue, would you like to process the queue now? (y/n): ")
    if answer.strip().lower() == "y":
        return True
    elif answer.strip().lower() == "n":
        return False
    logger.debug('ERROR: Bad input. Asking again.')
    return processConfirm()

def convertEntry(i, foundID, root):
    name = i['name']

    #Convert status
    stat = i['status']
    if stat == 'watched': stat = 'Completed'
    elif stat == 'watching': stat = 'Watching'
    elif stat == 'want to watch': stat = 'Plan to Watch'
    elif stat == 'stalled': stat = 'On-Hold'
    elif stat == 'dropped': stat = 'Dropped'
    elif stat == "won't watch": return False

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


def processList():
    data = loadJSON(args.anime_list)

    #Start MAL XML structure
    root = ET.Element('myanimelist')
    info = ET.SubElement(root, 'myinfo')
    uname = ET.SubElement(info, 'user_name')
    total = ET.SubElement(info, 'user_total_anime')
    uname.text = data['user']['name']


    cachedEntries, notFoundEntries, badEntries = getInitialCounts(data, root)

    skipSearch = False
    if len(notFoundEntries) <= 0:
        skipSearch = True
        logger.info("All entries found, processing converted list...")
    elif args.cache_only or processConfirm() == False:
        skipSearch = True
        logger.info("Skipping search, processing cache-only converted list...")

    foundEntries = []

    if skipSearch == False:
        foundEntries = searchEntries(notFoundEntries, root)

    totalCount = len(data['entries'])
    cacheFound = len(cachedEntries)
    badFound = len(badEntries)
    searchFound = len(foundEntries)
    notFound = len(notFoundEntries)

    total.text = str(cacheFound + searchFound)

    #Export XML to convert file
    #tree = ET.ElementTree(root)
    dom = minidom.parseString(ET.tostring(root))
    dom = dom.toprettyxml(indent='\t')
    with open('convert.xml', 'w', encoding='utf-8') as f2:
        f2.write(dom)
    
    print("=================================")
    logger.info("Total Entries: "+str(totalCount))
    logger.info("Cache Found: "+str(cacheFound))
    logger.info("Bad Found: "+str(badFound))
    logger.info("Search Found: "+str(searchFound))
    logger.info("Not Found: "+str(notFound))

def unmapped(name, unmapped_file):
    with open(unmapped_file, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow([name])

def removeUnmapped(name):
    with open(args.unmapped_file, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        data = list(reader)

    row = False
    rowNum = 0
    for i in data:
        if i[0] == name:
            row = rowNum
            break
        rowNum += 1

    newRows = data[:row] + data[row+1:]

    with open(args.unmapped_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerows(newRows)

def unmappedCheck(name, unmapped_file):
    with open(unmapped_file, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        data = list(reader)

    for i in data:
        if i[0] == name:
            return True
        
    return False

def searchQueue():
    with open(args.unmapped_file, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        data = list(reader)

    queueTotal = len(data)

    count = 0
    foundEntries = []
    #notFoundEntries = []
    print("PROGRESS: " + str(count) + " / " + str(queueTotal))
    for name in data:
        if count < args.offset:
            count += 1
            continue

        #Use this for smaller tests
        limit = args.limit
        if limit > -1 and count >= limit:
            break

        name = name[0]

        foundID = False
        count += 1
        
        foundID = search(name)

        if foundID == -1:
            logger.info("Quitting program...")
            break

        if foundID == False:
            #notFound += 1
            #notFoundEntries.append(name)
            #MUST use 4 second delay for Jikan API rate limits
            #delayCheck(args.api_delay)
            if args.skip_confirm == False:
                os.system('clear')
            print("PROGRESS: " + str(count) + " / " + str(queueTotal))
            continue

        foundEntries.append(foundID)
        cache(name, foundID)
        removeUnmapped(name)

        if args.skip_confirm == False:
            os.system('clear')

        strlog = name + " ---> " + foundID
        logger.info("Added to cache: "+strlog)
        print("PROGRESS: " + str(count) + " / " + str(queueTotal))

        #MUST use 4 second delay for Jikan API rate limits
        #delayCheck(args.api_delay)


    searchFound = len(foundEntries)
    notFound = queueTotal

    print("=================================")
    logger.info("Search Found: "+str(searchFound))
    logger.info("Not Found: "+str(notFound))

def main():
    if args.search_queue:
        searchQueue()
        return

    processList()

def script_timer():
    end_time = datetime.datetime.now()
    process_time = end_time - start_time
    print()
    print(process_time)

if __name__ == "__main__":
    main()
    # script_timer()
