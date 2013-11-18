from twisted.internet import reactor, defer
from twisted.words.protocols import irc
from twisted.internet.protocol import ReconnectingClientFactory
from twisted.words.service import IRCUser
from twisted.internet.task import LoopingCall

from types import FunctionType
import time, sys, os, locale, logging
import ConfigManager

class RoiBot(irc.IRCClient):

    pendingWhoisTests = {}
    channelTopics = {}
    ns = {}

    def __init__(self, nick, logger):
        self.nickname = nick
        self.realname = "lp:roibot"
        # this must used when getting the new settings from the config manager since
        # twisted may have added an underscore to self.nickname in case the nick
        # has been stolen by someone on IRC
        self.nickInConfigFile = nick 
        self.logger = logger
        self.watchdog = LoopingCall(self._sendPing)

    def _sendPing(self):
        self.sendLine("PING " + self.factory.config.server)

    def _parseIgnoreList(self):
        """ Parses the plugin ignore list. """
        self.ignored = {}
        try:
            filename = os.path.join(sys.path[0], "modules"+os.path.sep+"ignore")
            f = open(filename)
            lines = None
            try:
                lines = f.readlines()
            finally:
                f.close()

            for i, line in enumerate(lines):
                target = line.split(':')[0].split('@')
                if len(target) == 1:
                    err = "Error while parsing the plugin ignore list line %d."
                    self.logger.error(err % i)
                    continue
                channel, server = target[0].strip(), target[1].strip()
                modules = line.split(':')[1].strip().replace('\n', '').replace('\r', '').split(' ')
                self.ignored[channel+server] = modules

        except IOError, ioe:
            err = "An error occurred while reading the file modules"+os.path.sep+"ignore"
            self.logger.warn(ioe)

    def _findModules(self):
        """ Find all modules """
        self.moduledir = os.path.join(sys.path[0], "modules/")
        self.modules = [m for m in os.listdir(self.moduledir) if m.endswith(".py")]

    def _loadModules(self):
        self.ns = {}

        for module in self.modules:
            # env = self._getGlobals()
            env = {}
            execfile(os.path.join(self.moduledir, module), env, env)
            self.ns[module] = (env, env)

    def _runCommand(self, cmd, channel, user, msg):
        for module, env in self.ns.items():
            myglobals, mylocals = env
            for name, ref in mylocals.items():
                if name == cmd and type(ref) == FunctionType:
                    # check if the plugin has been disabled on the given channel
                    key = channel + self.factory.config.server
                    if key in self.ignored and module in self.ignored[key]:
                        continue

                    ref(self, channel, user, msg)

    def privmsg(self, user, channel, msg):
        """This will get called when the bot sees someone do an action."""
#        print user + "at " + channel + " said " + msg + "\n"
        try:
            cmd = None
            if msg.startswith('.'):
                cmd = msg.split()[0].decode('utf-8', 'strict')
            msg = msg.decode('utf-8', 'strict')
        except UnicodeDecodeError, e:
            try:
                if msg.startswith('.'):
                    cmd = msg.split()[0].decode('iso-8859-1', 'strict')
                msg = msg.decode('iso-8859-1', 'strict')
            except UnicodeDecodeError, e:
                return

        if msg.startswith('.'):
            cmd = cmd.replace(u'\u00E4', 'a').replace(u'\u00F6', 'o')
            print 'user at ' +channel + ' said ' + msg + '\n'

            if cmd == ".rehash":
                try:
                    self.factory.cm.parse()
                    self.factory.config = self.factory.cm.getConfig(self.nickInConfigFile)
                except ConfigException, e:
                    sendMessage(channel, user, "Error while parsing the settings")
                    self.logger.error(str(e))
                self._findModules()
                self._loadModules()
                self._parseIgnoreList()
            else:
                if len(msg.split()) > 1:
                    msg = msg.split(' ', 1)[1]
                else:
                    msg = None
                self._runCommand("handle_"+cmd[1:], channel, user, msg)
        else:
            self._runCommand("process_line", channel, user, msg)

    def sendMessage(self, channel, user, msg):
        if not channel or channel == self.nickname:
            if not user:
                raise ValueErro("Illegal arguments given. Please specify a user or channel.")
            else:
                self.msg(user.split('!')[0], msg)
        else:
            self.say(channel, msg)

     
    def addOp(self, whoisParams, channel):
        """Adds a new channel operator"""
        ident = whoisParams[2]
        hostmask = whoisParams[3]

        if ident[0] in ['+', '~','^']:
            ident = ident[1:]

        usermask = ident + '@' + hostmask
        try:
            self.factory.cm.addOp(self.nickname, channel, usermask)
        except ConfigException, e:
            self.logger.error(str(e))
            say(channel, "Unexpected error occurred.")

    def isAdmin(self, user):
        """ Check if an user has admin privileges.
        @type user: string
        @param user: ident@host """

        return user == self.factory.config.admin

    def isOperator(self, channel, user):
        """ Check if an user has channel operator privileges.
        @type user: string
        @param user: ident@host
        @param channel: channel"""

        try:
            return user in self.factory.config.ops[channel]
        except (KeyError, TypeError):
            return False

    def removeBan(self, hostmask, channel):
        self.mode(channel, False, 'b', None, None, hostmask) 

    def kickUser(self, whoisParams, channel, nick, reason):
        if not reason:
            self.kick(channel, nick, 'ei')
        else:
            self.kick(channel, nick, reason)

    def unbanUser(self, whoisParams, channel, timeout, hostmask):
        if hostmask:
            self.mode(channel, False, 'b', None, None, hostmask) 
        else:
            self.mode(channel, False, 'b', None, None, whoisParams[3]) 

    def banUser(self, whoisParams, channel, timeout, hostmask):
        if hostmask:
            self.mode(channel, True, 'b', None, None, hostmask) 
        else:
            self.mode(channel, True, 'b', None, None, whoisParams[3]) 

        # when the timeout occurs, remove the ban
        if timeout:
            reactor.callLater(timeout * 60, self.removeBan, whoisParams[3], channel)

    def irc_RPL_WHOISUSER(self, prefix, params):
        nick = params[1]
        if nick in self.pendingWhoisTests:
            self.pendingWhoisTests[nick].callback(params)
            del self.pendingWhoisTests[nick]

    def irc_RPL_TOPIC(self, prefix, params):
        for i in params:
            self.channelTopics[params[1]] = params[2];

     # send a topic query when the bot joins a channel
    def joined(self, channel):
        self.topic(channel, None)
       
    def connectionMade(self):
        irc.IRCClient.connectionMade(self)
        self.watchdog.start(120)
        #self.nickname = self.factory.settings['nick']
        self.logger.info("Connection made.")

    def connectionLost(self, reason):
        self.watchdog.stop()
        self.logger.warn("Connection lost. Reason: %s" % reason)
        irc.IRCClient.connectionLost(self, reason)

    def signedOn(self):
        """Called when bot has succesfully signed on to server."""
        self.logger.info("Signed on to the server.")

        self._findModules()
        self._loadModules()
        self._parseIgnoreList()

        for module, env in self.ns.items():
            myglobals, mylocals = env
            for name, ref in mylocals.items():
                if name == "signed_on" and type(ref) == FunctionType:
                    ref(self, self.factory.config.nickname)

        for channel in self.factory.config.channels:
            self.join(channel)
            print channel


class BotFactory(ReconnectingClientFactory):

    """ A factory for Bots """
    """ A new protcol instance will be created each time we connect to the server """

    maxDelay = 7200
    factor = 3
    initialDelay = 100

    def __init__(self, config, cm):
        self.config = config
        self.cm = cm
        logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s',
                    filename=self.config.nickname+'.log',
                    filemode='a')
        self.logger = logging.getLogger()


    def buildProtocol(self, addr):
        self.logger.info("Connected")
        self.logger.info("Resetting reconnection delay")
        self.resetDelay
        p = RoiBot(self.config.nickname, self.logger)
        p.factory = self
        return p

    def clientConnectionLost(self, connector, reason):
        self.logger.warn("Connection lost. Reason: %s" % reason)
        ReconnectingClientFactory.clientConnectionLost(self, connector, reason)

    def clientConnectionFailed(self, connector, reason):
        self.logger.warn("Connection failed. Reason: %s" % reason)
        ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)


if __name__ == '__main__':

    if len(sys.argv) < 2:
        print 'Please give the name of the config file'
        sys.exit(1)

    locale.setlocale(locale.LC_ALL, 'en_US.utf8')

    cm = ConfigManager.ConfigManager(sys.argv[1])

    for bot in cm.bots:
        f = BotFactory(bot, cm)
        reactor.connectTCP(bot.server, bot.port, f)

    reactor.run()
