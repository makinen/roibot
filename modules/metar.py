import unicodedata
import pymetar
import yaml

stations = {}

def load_config(bot):
    global stations
    try:
        f = file('modules/metar.yaml', 'r')
        stations = yaml.load(f)
        f.close()
    except Exception, e:
        bot.logger.error(str(e))

def add_station(name, code, bot, channel,user):
    global stations

    if not stations:
        stations = {}
    stations[name] = code
    try:
        f = file('modules/metar.yaml', 'w')
        yaml.dump(stations, f, default_flow_style=False)
        f.close()
        load_config(bot)
    except Exception, e:
        bot.sendMessage(channel, user, 'Unexpected error occurred')
        bot.logger.error(str(e))

def show_metar_stations(bot, channel,user):
    if not stations:
        answer = "Known stations: "
        bot.sendMessage(channel, user,answer.encode('utf-8'))
        return

    st = stations.keys()
    st.sort()
    answer = "Known stations: "
    answer += "".join([x == max(st) and x or x + ', ' for x in st])
    bot.sendMessage(channel, user,answer.encode('utf-8'))


def handle_metar(bot, channel, user, station):

    if not stations:
        load_config(bot)

    if not station:
        show_metar_stations(bot,channel, user)
        return

    if station.startswith('rehash'):
        load_config(bot)
        return


    if station.startswith('add'):
        if (len(station.split()) == 3):
            name = station.split()[1]
            code = station.split()[2]
            add_station(name, code, bot, channel, user)
            return

    if station == 'stations':
        show_metar_stations(bot, channel, user)
        return

    station = station[0].capitalize() + station[1:]


    if station in stations:
        station = stations[station]

    rf=pymetar.ReportFetcher(station)
    try:
        rep=rf.FetchReport()
    except pymetar.NetworkException, e:
        bot.sendMessage(channel, user, 'Station not found')
        return

    rp=pymetar.ReportParser()
    pr=rp.ParseReport(rep)

    answer = '%s (%.3f%s, %.3f%s) %s: temperature: %s, Weather: %s, Humidity: %s, Pressure: %s, Visibility: %s, Wind: %s' %\
            (pr.getStationName(),\
            pr.getStationPositionFloat()[0], u'\u00B0',\
            pr.getStationPositionFloat()[1],u'\u00B0',\
            pr.getTime(),\
            pr.getTemperatureCelsius() and str(pr.getTemperatureCelsius()) + u'\u00B0' + 'C' or 'unknown',\
            pr.getSkyConditions() and pr.getSkyConditions() or 'unknown',\
            pr.getHumidity() and str(pr.getHumidity()) + '%' or 'unknown',\
            pr.getPressure() and '%.3f hPa' % pr.getPressure() or 'unknown',\
            pr.getVisibilityKilometers() and "%.3f km" % pr.getVisibilityKilometers() or 'unknown' ,\
            pr.getWindSpeed() and "%.3f m/s" % pr.getWindSpeed() or 'unknown')

    answer= answer.encode('utf-8')

    bot.sendMessage(channel, user, answer)

