from jikanpy import Jikan
from xml.dom import minidom
import xml.etree.cElementTree as ET
import json, time, datetime, math

delay = 4
logfile = 'log.txt'
qtime = datetime.datetime.now()

#Anime Planet JSON files
test1 = "samples/export-anime-SomePoorKid.json"
test2 = "samples/export-anime-princessdaisy41_2.json"

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

    with open(logfile, 'a') as f:
        f.write(strlog + '\n')
    print(strlog)

def delayCheck():
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
        return jname

    found = optionsCheck(name, jdata)
    if found != False:
        return str(jdata['results'][found]['title'])

    print()
    print('Initial title: ' + name)
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
    elif v1.strip().lower() == 'y': return jname
    else:
        print('ERROR: Bad input. Asking again.')
        return verify1(name, jname, jdata)
    return False

def verify2(options):
    q2 = 'Enter number for correct choice: '
    v2 = input(q2)
    if v2.strip() == '0': return False
    elif int(v2) != False: return options[int(v2)-1]
    else:
        print('ERROR: Bad input. Asking again.')
        return verify2(options)
    return False

def main():
    #Make log and load data
    createLog()
    data = loadJSON(test1)

    #Start XML structure
    root = ET.Element('myanimelist')
    info = ET.SubElement(root, 'myinfo')
    uname = ET.SubElement(info, 'user_name')
    total = ET.SubElement(info, 'user_total_anime')
    uname.text = data['user']['name']
    total.text = str(len(data['entries']))

    #Initiate Jikan
    jikan = Jikan()
    
    count = 0
    store = []
    
    for i in data['entries']:
        count = count + 1
        
        name = i['name']
        name = name.replace('&','and')
        
        if len(i['name']) < 3:
            log(1, i['name'])
            delayCheck()
            continue
        
        try:
            jfile = jikan.search('anime', name)
        except:
            log(2, i['name'])
            delayCheck()
            continue
        
        jdata = json.loads(json.dumps(jfile))
        jname = jverify(i['name'], jdata)
        if jname == False:
            log(2, i['name'])
            delayCheck()
            continue
        
        if jname in store:
            log(3, i['name'], jname)
            delayCheck()
            continue
        
        store.append(jname)

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
        
        title.text = name
        status.text = stat
        weps.text = str(i['eps'])
        malid.text = str(jdata['results'][0]['mal_id'])
        if str(i['started']) == "None": wsd.text = "0000-00-00"
        else: wsd.text = str(i['started']).split()[0]
        if str(i['completed']) == "None": wfd.text = "0000-00-00"
        else: wfd.text = str(i['completed']).split()[0]
        score.text = str(int(i['rating']*2))
        twatched.text = str(i['times'])

        log(0, i['name'], jname, count)

        #Use this for smaller tests
        #if count >= 10:
        #    break

        #MUST use 4 second delay for Jikan's rate limit
        delayCheck()

    #Export XML to convert file
    tree = ET.ElementTree(root)
    dom = minidom.parseString(ET.tostring(root))
    dom = dom.toprettyxml(indent='\t')
    with open('convert.xml', 'w') as f2:
        f2.write(dom)


if __name__ == "__main__":
    main()
