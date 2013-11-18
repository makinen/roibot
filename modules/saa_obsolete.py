from BeautifulSoup import BeautifulSoup
import urllib
import re
import unicodedata

cities = None

def unicode_to_ascii(value):
	unicode_to_ascii = {u'\u00E4' : 'a', u'\u00C4' : 'A', u'\u00F6' : 'o',\
			    u'\u00D6' : 'O', u'\u00C5': 'A', u'\u00E5': 'a'}
	for i in unicode_to_ascii:
		 value = value.replace(i, unicode_to_ascii[i])
	return value

def html_to_unicode(value):
	html_to_unicode = {'&deg;': u'\u00B0', '&nbsp;': ' ', '&auml;': u'\u00E4',\
    '; ': '', '&Auml;': u'\u00C4', '&Ouml': u'\u00C5', '&ouml;': u'\u00F6', \
    '&aring;': u'\u00E5'}
	for i in html_to_unicode:
		 value = value.replace(i, html_to_unicode[i])
	return value

def fetch_cities():
	global cities
	url = "http://www.fmi.fi/saa/paikalli.html"
	htmlfile = urllib.urlopen(url)
	doc = htmlfile.readlines()
	htmlfile.close()
	soup = BeautifulSoup("".join(doc))
	select = soup.find('select', {"name": "place"})
	options = select.findAll('option')

	cities = [html_to_unicode(o.string) for o in options if o.string != None]

def get_html_document(city, station):
    city = unicode_to_ascii(city)
    if not station:
        url = "http://legacy.fmi.fi/saa/paikalli.html?place="+city
    else:
        url = "http://legacy.fmi.fi/saa/paikalli.html?station="+station+"&place="+city
    htmlfile = urllib.urlopen(url)
    doc = htmlfile.readlines()
    htmlfile.close()
    soup = BeautifulSoup("".join(doc))
    return soup

def get_weather_by_city_prefix(channel, user, bot, prefix):
    
    prefix = prefix[0].capitalize() + prefix[1:]
    if not cities:
        fetch_cities()

    answer = None
    for city in cities:
        if city.startswith(prefix):
            soup = get_html_document(city, None)
            station = get_selected_station(soup, city)
            data = parse_weather(soup)
            if not data:
                break

            if answer:
                answer += format_data(data, station, city)
            else:
                answer = format_data(data, station, city)

           # parse weather data from additional stations if available 
            stations = get_additional_stations(soup, city)
            for station in stations:
                code, name = station
                soup = get_html_document(city, code)
                data = parse_weather(soup)
                answer += ' ' + format_data(data, name, None)
    return answer

def get_selected_station(soup, city):
    select = soup.find('select', {"name": "station"})

    if not select:
        return None
    station = select.find('option', {"selected": "selected"}).string

    if station.startswith(city[:len(city)/2]):
        station = station.split(' ')[1]
    return html_to_unicode(station)

def get_additional_stations(soup, city):
    select = soup.find('select', {"name": "station"})
    if not select:
        return {}
    options = select.findAll('option')
    stations = []
    
    #the first station's data has already been fetched
    for o in options[1:]:
        code = o['value']
        if not o.string:
            continue
        name = html_to_unicode(o.string).replace(city+" ", "")
        if name.startswith(city[:len(city)/2]):
            name = name.split(' ')[1]
        stations.append((code,name))
    
    return stations
    
def handle_saa_obsolete(bot, channel, user, city):

    if not city:
        city = "Rovaniemi"

    if city == "hell":
        city = "Helsinki"

    if city == 'lappeen  Ranta' or city == 'lappeen Ranta' or city == 'lappeen ranta':
        city = "Lappeenranta"

    if len(city) < 3:
        return

    city = city.lower()

    answer = get_weather_by_city_prefix(channel, user, bot, city)
    if not answer:
        answer = "Kaupungille "+city+" ei l"+u'\u00F6'+"ydy s"+u'\u00E4'+u'\u00E4'+"tietoja."
        
    answer = answer.encode('utf-8')
    bot.sendMessage(channel, user, answer)

class Weather:
    temperature = None
    humidity = None
    wind = None
    wind_direction = None
    puuska = None

def parse_weather(soup):

    weather = Weather()
    
    if soup.findAll(text=re.compile("deg")):
        weather.temperature = html_to_unicode(soup.findAll(text=re.compile("deg"))[0])

    if soup.findAll(text=re.compile("[0-9]*&nbsp;%")):
        weather.humidity = html_to_unicode(soup.findAll(text=re.compile("[0-9]*&nbsp;%"))[0])

    if soup.findAll(text=re.compile("tyynt")):
        weather.wind_direction = 'tyynt' + u'\u00E4'
    else:
        if soup.findAll(text=re.compile("tuulta")):
            direction = soup.findAll(text=re.compile("tuulta"))[0]
            weather.wind_direction = html_to_unicode(direction.lower()).strip()
            weather.wind = html_to_unicode(soup.findAll(text=re.compile("m/s"))[0])
    
    if soup.findAll(text=re.compile("puuska")):
        if len(soup.findAll(text=re.compile("m/s"))) > 1:
            weather.puuska = html_to_unicode(soup.findAll(text=re.compile("m/s"))[1])
            #puuska = ''.join(c for c in puuska if c.isdigit())

    return weather

def format_data(data, station, city):

    if not station:
        answer = data.temperature and data.temperature+', ' or ""
        answer += data.humidity and data.humidity or ""
        if answer is not "":
            answer+=", "
    else:
        answer = data.temperature and data.temperature+', ' or ""
        answer += data.humidity and data.humidity or ""
        if answer is not "":
            answer+=", "
        station = station[0].capitalize() + station[1:]
        if not city:
            station = u'\u0002'+station+u'\u000F'
        answer = station + ": " + answer

    if city:
        answer = u'\u0002'+city+" "+u'\u000F'+answer
    
    map = {'l'+u'\u00E4'+'nsituulta': 'l'+u'\u00E4'+'nsi', 'pohjoistuulta': 'pohjoinen',\
    'koillistuulta': 'koillinen', 'luoteistuulta': 'luode', 'lounaistuulta': 'lounas',\
    'kaakkoistuulta': 'kaakko', 'it'+u'\u00E4'+'tuulta': 'it'+u'\u00E4',\
    'etel'+u'\u00E4'+'tuulta': 'etel'+u'\u00E4'}
    if data.wind_direction and data.wind_direction in map:
        data.wind_direction = map[data.wind_direction]


    if data.wind:
        answer += '%s ' % data.wind
    if data.puuska:
        answer += '(%s) ' % data.puuska
    if data.wind_direction:
        answer += '%s' % data.wind_direction

    answer = answer.strip()
    if answer[len(answer)-1:len(answer)] == ',':
        answer = answer[:len(answer)-1]

    return answer


if __name__ == '__main__':
    handle_saa(None, None, None, "Espoo")
    handle_saa(None, None, None, "Rovaniemi")
    handle_saa(None, None, None, "Helsinki")
    handle_saa(None, None, None, "Turku")
    handle_saa(None, None, None, "Inari")
    handle_saa(None, None, None, "Tampere")
    handle_saa(None, None, None, "Rauma")
    handle_saa(None, None, None, "xxx")
    handle_saa(None, None, None, "")
    handle_saa(None, None, None, None)
