import time, re 
from twisted.internet import reactor, defer
from types import FunctionType

p = re.compile('.+!.+@.+\..+')

def parse_user(user):
    usernick = user.split('!')[0]
    usermask = user.split('!')[1]
    if usermask[0] in ['+', '~', '^']:
        usermask = usermask[1:]
 
    return (usernick, usermask)

def parse_msg(bot, channel, msg):
    if msg:
        msg = msg.encode("utf-8")
        msg = msg.split(' ')

    if channel == bot.nickname:
        target_channel = msg[0]
        msg = msg[1:]
    else:
        target_channel = channel

    return (target_channel, msg)

def handle_time(bot, channel, user, msg):
    bot.sendMessage(channel, user, time.asctime(time.localtime(time.time())))

# TODO this should be in the RoiBot class and gather the commands from
# the other plugins too
def handle_ls(bot, channel, user, msg):
    cmds = []
    gs = globals()
    for i in gs.keys():
        if i.startswith("handle_") and type(gs[i]) is FunctionType:
            cmds.append(i[len("handle_"):])

    cmds.sort()
    cmds = ', '.join(cmds)
    i = cmds.rfind(',')
    cmds = "Available commands: " + cmds[:i] + ' and ' + cmds[i+2:]
    bot.sendMessage(channel, user, cmds)

def handle_quit(bot, channel, user, msg):
    usernick, usermask = parse_user(user)
    if bot.isAdmin(usermask):
        bot.quit()
        reactor.stop()

def handle_op(bot, channel, user, msg):
    usernick, usermask = parse_user(user)
    target_channel, arguments = parse_msg(bot, channel, msg)

    if bot.isOperator(target_channel, usermask):
        # op the user from who we got the command
        if not arguments:
            bot.mode(target_channel, True, 'o', None, usernick, None) 
        else:
            for nick in arguments:
                bot.mode(target_channel, True, 'o', None, nick, None) 

def handle_echo(bot, channel, user, msg):
    usernick, usermask = parse_user(user)
    target_channel, arguments = parse_msg(bot, channel, msg)

    if bot.isOperator(target_channel, usermask):
        bot.sendMessage(target_channel, user, ''.join(arguments))

def handle_msg(bot, channel, user, msg):
    usernick, usermask = parse_user(user)
    if len(msg.split(' ')) >= 2:
        msg = msg.encode("utf-8")
        target_channel = None
        target_user = None
        if msg.split(' ')[0].startswith('#'):
            target_channel = msg.split(' ')[0]
        else:
            target_user = msg.split(' ')[0]

        message = ' '.join(msg.split(' ', 1)[1:])
        if bot.isOperator(target_channel, usermask):
            bot.sendMessage(target_channel, None, message)
        elif bot.isOperator(channel, usermask):
            bot.sendMessage(None, target_user, message)

def handle_topic(bot, channel, user, msg):
    usernick, usermask = parse_user(user)
    target_channel, arguments = parse_msg(bot, channel, msg)
    topic = ' '.join(arguments)

    if bot.isOperator(target_channel, usermask):
        bot.channelTopics[target_channel] = topic
        bot.topic(target_channel, topic)

def handle_ta(bot, channel, user, msg):
    usernick, usermask = parse_user(user)
    target_channel, arguments = parse_msg(bot, channel, msg)
    topic = ' '.join(arguments)

    if bot.isOperator(target_channel, usermask):
        if target_channel in bot.channelTopics:
            bot.channelTopics[target_channel] = topic + ' | ' + bot.channelTopics[target_channel]
        else:
            bot.channelTopics[target_channel] = topic

        bot.topic(target_channel, bot.channelTopics[target_channel])

def handle_td(bot, channel, user, msg):
    usernick, usermask = parse_user(user)
    target_channel, arguments = parse_msg(bot, channel, msg)
    topic = ' '.join(arguments)

    if bot.isOperator(target_channel, usermask):
        t = bot.channelTopics[target_channel].split('|')
        topicTmp = [e.strip() for i,e in enumerate(t) if str(i) not in topic.split()]
        # put a separator char between two parts of the topic
        for i, e in enumerate(topicTmp[1:]):
            topicTmp[i+1] = ' | ' + e

        newTopic = "".join(topicTmp)

        # Change channel's topic if it's not the same as the old one
        if newTopic != bot.channelTopics[target_channel]:
            bot.channelTopics[target_channel] = newTopic
            bot.topic(target_channel, newTopic)

def handle_k(bot, channel, user, msg):
    handle_kick(bot, channel, user, msg)

def handle_kick(bot, channel, user, msg):
    usernick, usermask = parse_user(user)
    target_channel, arguments = parse_msg(bot, channel, msg)

    if bot.isOperator(target_channel, usermask):
        if len(arguments) == 2:
            bot.kickUser(None, target_channel, arguments[0], arguments[1])
        else:
            bot.kickUser(None, target_channel, arguments[0], None)

def handle_b(bot, channel, user, msg):
    handle_ban(bot, channel, user, msg)

def handle_ban(bot, channel, user, msg):
    usernick, usermask = parse_user(user)
    target_channel, arguments = parse_msg(bot, channel, msg)
    # check whether we got a hostmask or a nickname
    if p.search(arguments[0]):
        hostmask = arguments[0]
        ban(bot, target_channel, usermask, hostmask, None, bot.banUser)
    else:
        nick = arguments[0]
        ban(bot, target_channel, usermask, None, nick, bot.banUser)

def handle_unban(bot, channel, user, msg):
    usernick, usermask = parse_user(user)
    target_channel, arguments = parse_msg(bot, channel, msg)
    # check whether we got a hostmask or a nickname
    if not arguments:
        return
    if p.search(arguments[0]):
        hostmask = arguments[0]
        ban(bot, target_channel, usermask, hostmask, None, bot.unbanUser)
    else:
        nick = arguments[0]
        ban(bot, target_channel, usermask, None, nick, bot.unbanUser)


def ban(bot, target_channel, usermask, troublemaker_hostmask, troublemaker_nick, func):
    if bot.isOperator(target_channel, usermask):
        if troublemaker_hostmask:
            bot.banUser(None, target_channel, None, troublemaker_hostmask)
        else:
            # get troublemaker's hostmask
            bot.sendLine('WHOIS %s' % troublemaker_nick)
            d = defer.Deferred()
            d.addCallback(func, channel = target_channel, timeout = None, hostmask = None)

            # add the nick to the dictionary of pending whois queries
            bot.pendingWhoisTests[troublemaker_nick] = d
            return d

def handle_kb(bot, channel, user, msg):
    handle_kickban(bot, channel, user, msg)

def handle_kickban(bot, channel, user, msg):
    usernick, usermask = parse_user(user)
    target_channel, arguments = parse_msg(bot, channel, msg)
    if bot.isOperator(target_channel, usermask) and arguments:
        nick = arguments[0]
        reason = len(arguments) >= 2 and ' '.join(arguments[1:]) or None

        # get troublemaker's hostmask
        bot.sendLine('WHOIS %s' % nick)

        d = defer.Deferred()
        d.addCallback(bot.banUser, channel = target_channel, timeout = None, hostmask = None)
        d.addCallback(bot.kickUser, channel = target_channel, nick = nick, reason = reason)
        bot.pendingWhoisTests[nick] = d

        return d

def handle_kn(bot, channel, user, msg):
    handle_knockout(bot, channel, user, msg)

def handle_knockout(bot, channel, user, msg):
    usernick, usermask = parse_user(user)
    target_channel, arguments = parse_msg(bot, channel, msg)
    if not arguments:
        return

    if bot.isOperator(target_channel, usermask):
        try:
            timeout = int(arguments[0])
            arguments.remove(arguments[0])
        except ValueError:
            timeout = 10

        nick = arguments[0]
        reason = len(arguments) >= 2 and ' '.join(arguments[1:]) or None

        # get troublemaker's hostmask
        bot.sendLine('WHOIS %s' % nick)

        d = defer.Deferred()
        d.addCallback(bot.banUser, channel = target_channel, timeout = timeout, hostmask = None)
        d.addCallback(bot.kickUser, channel = target_channel, nick = nick, reason = reason)
        bot.pendingWhoisTests[nick] = d

        return d
        
def handle_addop(bot, channel, user, msg):
    usernick, usermask = parse_user(user)
    target_channel, arguments = parse_msg(bot, channel, msg)
    if bot.isAdmin(usermask):
        for nick in arguments:
            bot.sendLine('WHOIS %s' % nick)
            d = defer.Deferred()
            d.addCallback(bot.addOp, channel = target_channel)
            bot.pendingWhoisTests[nick] = d

def handle_voice(bot, channel, user, msg):
    usernick, usermask = parse_user(user)
    target_channel, arguments = parse_msg(bot, channel, msg)

    # check out that we were given a nick and not a channel by an accident
    # TODO move this to the parse_msg method
    if not arguments or arguments[0].startswith("#"):
        return

    if bot.isOperator(target_channel, usermask):
        bot.mode(target_channel, True, 'v', None, ' '.join(arguments), None) 

def handle_join(bot, channel, user, msg):
    usernick, usermask = parse_user(user)

    if not bot.isAdmin(usermask):
        return

    if not msg:
        return

    bot.join(msg.encode('utf-8'))

def handle_part(bot, channel, user, msg):
    usernick, usermask = parse_user(user)

    if not bot.isAdmin(usermask):
        return

    if not msg:
        bot.leave(channel.encode('utf-8'))
    else:
        bot.leave(msg.encode('utf-8'))
