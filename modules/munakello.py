from twisted.internet import reactor, defer

def handle_munakello(bot, channel, user, message):

    timeout, alert_msg = message.split(' ', 1)
    try:
        timeout = int(timeout)
    except ValueError:
        bot.sendMessage(channel, user, "Not an integer %s, " % timeout)
        return

    reactor.callLater(timeout * 60, alert, bot, channel, user, alert_msg)

def alert(bot, channel, user, message):
    nick = user.split('!')[0]
    message = nick + ": " + message
    bot.sendMessage(channel, user, message.encode('utf-8'))
