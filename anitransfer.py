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

from jikanpy import Jikan

DEFAULTS = {
    'jikan_delay': 4, # in seconds
    'cache_file': 'cache.csv',
    'bad_file': 'bad.csv',
}

logfile = 'log.txt'
qtime = datetime.datetime.now()

#Anime Planet JSON files
test1 = "samples/export-anime-SomePoorKid.json"
test2 = "samples/export-anime-princessdaisy41_2.json"
test3 = "samples/export-anime-aztech101.json"
test4 = "samples/export-anime-crandor94.json"
file = test1

#Loads JSON file
def loadJSON(filename):
    f = open(filename)
    data = json.load(f)
    f.close()
    return data

#Creates log text file with datetime as name
def createLog():
    global logfile
    dtime = datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S')
    logfile = 'logs/log_' + dtime + '.txt'
    f = open(logfile, 'w')
    f.close()

#Prints logs and errors and appends to log file
def log(type, name, jname=None, count=0):
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
        '--cache-file',
        help='Cache file to use for already downloaded anime mappings',
        default=DEFAULTS['cache_file']
    )
    parser.add_argument(
        '--bad-file',
        help='Cache file to use for incompatible anime mappings',
        default=DEFAULTS['bad_file']
    )

    options = parser.parse_args()
    return options

def main():
    #Make log and load data
    options = parse_arguments()
    createLog()
    data = loadJSON(file)

    #Start XML structure
    root = ET.Element('myanimelist')
    info = ET.SubElement(root, 'myinfo')
    uname = ET.SubElement(info, 'user_name')
    total = ET.SubElement(info, 'user_total_anime')
    uname.text = data['user']['name']
    total.text = str(len(data['entries']))

    count = 0

    for i in data['entries']:
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
        else: cached = True

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

        #Use this for smaller tests
        #if count >= 10:
        #    break

        #MUST use 4 second delay for Jikan's rate limit
        if cached == False:
            log(0, i['name'], mal[1], count)
            delayCheck()

    #Export XML to convert file
    tree = ET.ElementTree(root)
    dom = minidom.parseString(ET.tostring(root))
    dom = dom.toprettyxml(indent='\t')
    with open('convert.xml', 'w', encoding='utf-8') as f2:
        f2.write(dom)


if __name__ == "__main__":
    main()
