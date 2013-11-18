#!/usr/bin/python
# -*- coding: utf-8 -*-

import pywapi
import pprint

def handle_saa(bot, channel, user, message):

    city = message
    if not city:
        city = "Rovaniemi"

    result = pywapi.get_weather_from_google(city, 'FI')
    #{'current_conditions': {}, 'forecast_information': {}, 'forecasts': []

    if not result['current_conditions']:
        answer = "Weather condition for '%s' was not found.  " % city
        bot.sendMessage(channel, user, answer.encode('utf-8'))
        return

    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(result)

    celsius = " "+u'\u00B0'+"C"
    condition = result['current_conditions']['condition'].lower()
    humidity = result['current_conditions']['humidity'].lower()
    temp = result['current_conditions']['temp_c'].lower()+celsius
    wind = result['current_conditions']['wind_condition'].lower()

    city = u'\u0002'+city[0].capitalize() + city[1:]+u'\u000F'
    current = "%s %s, %s, %s, %s" % (city, temp, condition,humidity, wind)
    forecast = "("
    forecasts = result['forecasts']
    for day in forecasts:
        forecast += day['day_of_week'] + " " + day['low'] + "-"+day['high'] +celsius+ ", "
    forecast = forecast[:len(forecast)-2]+")"
    answer = current + " " + forecast
    bot.sendMessage(channel, user, answer.encode('utf-8'))


if __name__ == '__main__':
    class Printer:
        def sendMessage(*args, **kwargs):
            print args, kwargs

    test_line = "turku"

    handle_saa2(Printer(), None, None, test_line)
