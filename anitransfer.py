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

DEFAULTS = {
    'jikan_delay': 4, # in seconds
    'log_file': f'logs/log_{datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")}.txt',
    'cache_file': 'cache.csv',
    'bad_file': 'bad.csv',
    'skip_confirm': False,
    'cache_only': False,
    'limit': -1,
}

qtime = datetime.datetime.now()

#Loads JSON file
def loadJSON(filename):
    f = open(filename)
    data = json.load(f)
    f.close()
    return data

#Creates log text file with datetime as name
def createLog(logfile):
    f = open(logfile, 'w')
    f.close()

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

    return verify1(name, jname, jdata)

def verify1(name, jname, jdata):
    # q1 = 'Is this correct? [y/n]: '

    #skips the prompt if set
    skip = parse_arguments().skip_confirm
    if skip:
        # print(q1 + 'SKIP')
        print('SKIP')
        return False

    # v1 = input(q1)
    # if v1.strip().lower() == 'n':
        # return displayOptions(name, jdata)
    # elif v1.strip().lower() == 'y':
    #     return [jname, 0]
    return displayOptions(name, jdata)  #delete this when switching things back
    # print('ERROR: Bad input. Asking again.')
    # return verify1(name, jname, jdata)

def displayOptions(name, jdata):
    limit = 20
    options = []
    for i in jdata['data']:
        options.append(str(i['title']))
    print()
    # print('Initial title: ' + name)
    print('[OTHER OPTIONS]')
    x = 1
    for entry in jdata['data']:
        title = str(entry['title'])
        url = str(entry['url'])
        options.append(title)
        print('[' + str(x) + '] ' + title)
        print(url)
        print()
        if x >= limit:
            break
        x = x+1
    print('[i] Manual ID')
    print('[n] Skip entry')
    return verify2(options, limit)

def verify2(options, limit):
    v2 = input('Enter number for correct choice: ')
    if v2.strip() == '' or v2.strip() == 'n':
        return False
    elif v2.strip() == 'i':
        malID = input("Enter MAL ID: ")
        return malID
    elif v2.isdigit() and int(v2) <= limit:
        #print('option selected: ' + options[int(v2)-1])
        return [options[int(v2)-1], int(v2)-1]
    
    print('ERROR: Bad input. Asking again.')
    return verify2(options, limit)

def malSearch(name):
    print()
    print('Initial title: ' + name)

    if len(name) < 3:
        log(1, name)
        return False

    rname = name.replace('&','and')

    try:
        jikan = requests.get("https://api.jikan.moe/v4/anime?q="+rname)
        jfile = jikan.json()
    except:
        log(2, name)
        return False

    jdata = json.loads(json.dumps(jfile))
    if len(jdata['data']) == 0:
        log(2, name)
        return False

    jver = jverify(name, jdata)

    if jver == False:
        log(2, name)
        return False

    if isinstance(jver, str):
        return jver

    return [str(jdata['data'][jver[1]]['mal_id']), jver[0]]

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
        help='Skip any confirmation prompts that show up',
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
        '--limit',
        help='Limits the number of entries to process',
        default=DEFAULTS['limit'],
        type=int
    )
    parser.add_argument('anime_list')

    options = parser.parse_args()
    return options

def main():
    #Make log and load data
    options = parse_arguments()
    createLog(options.log_file)
    data = loadJSON(options.anime_list)

    #Start XML structure
    root = ET.Element('myanimelist')
    info = ET.SubElement(root, 'myinfo')
    uname = ET.SubElement(info, 'user_name')
    total = ET.SubElement(info, 'user_total_anime')
    uname.text = data['user']['name']
    total.text = str(len(data['entries']))

    count = 0

    cacheFound = 0
    searchFound = 0
    notFound = 0
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

        entryid = cacheSearch(name, options.cache_file)
        if entryid == False:
            if options.cache_only:
                print('CACHE ONLY: Skipping Jikan search')
                notFound += 1
                log(2, name)
                continue
            
            print('==============')
            mal = malSearch(name)
            if mal == False:
                delayCheck(options.jikan_delay)
                notFound += 1
                continue
            else:
                if isinstance(mal, str) == False:
                    mal = mal[0]
                cache(i['name'], mal, options.cache_file)
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
    #tree = ET.ElementTree(root)
    dom = minidom.parseString(ET.tostring(root))
    dom = dom.toprettyxml(indent='\t')
    with open('convert.xml', 'w', encoding='utf-8') as f2:
        f2.write(dom)

    print("=================================")
    print("Total Entries: "+str(len(data['entries'])))
    print("Cache Found: "+str(cacheFound))
    print("Search Found: "+str(searchFound))
    print("Not Found: "+str(notFound))


if __name__ == "__main__":
    main()
