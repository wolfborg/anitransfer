import json
from jikanpy import Jikan
from xml.dom import minidom
import xml.etree.cElementTree as ET

jikan = Jikan()

jfile = jikan.search('anime', '22/7')
jdata = json.loads(json.dumps(jfile))
print('22/7' + " : " + jdata['results'][0]['mal_id'])

root = ET.Element('myanimelist')

f = open("export-anime-SomePoorKid.json")
#f = open("export-anime-princessdaisy41_2.json")

data = json.load(f)

info = ET.SubElement(root, 'myinfo')
ET.SubElement(info, 'user_id')
uname = ET.SubElement(info, 'user_name')
uetype = ET.SubElement(info, 'user_export_type')
total = ET.SubElement(info, 'user_total_anime')
ET.SubElement(info, 'user_total_watching')
ET.SubElement(info, 'user_total_completed')
ET.SubElement(info, 'user_total_onhold')
ET.SubElement(info, 'user_total_dropped')
ET.SubElement(info, 'user_total_plantowatch')

uname.text = data['user']['name']
total.text = str(len(data['entries']))
uetype.text = '1'



for i in data['entries']:
    stat = i['status']
    if stat == 'watched': stat = 'Completed'
    elif stat == 'watching': stat = 'Watching'
    elif stat == 'want to watch': stat = 'Plan to Watch'
    elif stat == 'stalled': stat = 'On-Hold'
    elif stat == 'dropped': stat = 'Dropped'
    elif stat == "won't watch": continue
        
    entry = ET.SubElement(root, 'anime')
    malid = ET.SubElement(entry, 'series_animedb_id')
    title = ET.SubElement(entry, 'series_title')
    ET.SubElement(entry, 'series_type')
    ET.SubElement(entry, 'series_episodes')
    ET.SubElement(entry, 'my_id')
    weps = ET.SubElement(entry, 'my_watched_episodes')
    wsd = ET.SubElement(entry, 'my_start_date')
    wfd = ET.SubElement(entry, 'my_finish_date')
    ET.SubElement(entry, 'my_rated')
    score = ET.SubElement(entry, 'my_score')
    ET.SubElement(entry, 'my_dvd')
    ET.SubElement(entry, 'my_storage')
    status = ET.SubElement(entry, 'my_status')
    ET.SubElement(entry, 'my_comments')
    twatched = ET.SubElement(entry, 'my_times_watched')
    ET.SubElement(entry, 'my_rewatch_value')
    ET.SubElement(entry, 'my_tags')
    ET.SubElement(entry, 'my_rewatching')
    ET.SubElement(entry, 'my_rewatching_ep')
    uoi = ET.SubElement(entry, 'update_on_import')

    #title.text = "<![CDATA[" + i['name'] + "]]>"
    title.text = i['name']
    #try:
        #jfile = jikan.search('anime', i['name'])
    #except:
        #print("Error finding '" + i['name'] + "'")
    #jdata = json.loads(json.dumps(jfile))
    #malid.text = jdata['results'][0]['mal_id']
    
    status.text = stat
    weps.text = str(i['eps'])

    if str(i['started']) == "None": wsd.text = "0000-00-00"
    else: wsd.text = str(i['started']).split()[0]
    
    if str(i['completed']) == "None": wfd.text = "0000-00-00"
    else: wfd.text = str(i['completed']).split()[0]
    
    score.text = str(int(i['rating']*2))
    twatched.text = str(i['times'])

    uoi.text = '0'

tree = ET.ElementTree(root)
dom = minidom.parseString(ET.tostring(root))
dom = dom.toprettyxml(indent='\t')
with open('convert.xml', 'w') as f2:
    f2.write(dom)

f.close()
