import sys
import yaml
from yaml.scanner import ScannerError

class ConfigException(Exception):

    class CustomException(Exception):
        def __init__(self, *args):
            Exception.__init__(self, *args)
            self.wrapped_exc = sys.exc_info

class BotData():
    nickname = None
    channels = None
    ops = None
    server = None
    port = None
    admin = None

class ConfigManager():
    def __init__(self, filename):
        self.filename = filename
        self.bots = []
        self.parse()

    def getConfig(self, nick):
        for bot in self.bots:
            if bot.nickname == nick:
                return bot

    def parse(self):
        try:
            f = open(self.filename)
            self.data = yaml.load(f)
            f.close()
        except ScannerError, e:
            raise ConfigException, "Error while parsing the config file: " + str(e) 
        except IOError, (ErrorNumber, ErrorMessage):
            if ErrorNumber == 2:
                raise ConfigException, ErrorMessage + ': ' + self.filename
            else:
                raise ConfigException, ErrorMessage

        self.bots = []
        for bot in self.data.keys():
            b = BotData()
            self.bots.append(b)
            b.nickname = bot
            b.channels = self.data[bot]['channels'].keys()
            b.ops = dict(zip(b.channels, [self.data[bot]['channels'][k]['ops'] for k in b.channels]))
            b.server = self.data[bot]['server']
            b.port = self.data[bot]['port']
            b.admin = self.data[bot]['admin']

    def addOp(self, botnick, channel, usermask):
        """Adds a new user with channel operator privileges to the config file
           @param nickname
           @param channel
           @param usermask: ident@hostmask"""

        # TODO
        # self.data['channels'].setdefault(channel, {'ops': [usermask]})
        # self.data['channels'][channel].setdefault('ops', []).append(usermask)
        if not self.data[botnick]['channels'][channel]:
            self.data[botnick]['channels'][channel] = {'ops': [usermask]}
        elif not self.data[botnick]['channels'][channel]['ops']:
            self.data[botnick]['channels'][channel]['ops'] = [usermask]
        else:
            self.data[botnick]['channels'][channel]['ops'].append(usermask)
        
        try:
            f = file(self.filename, 'w')
            yaml.dump(self.data, f, default_flow_style=False)
            f.close()
        except IOError, (ErrorNumber, ErrorMessage):
            if ErrorNumber == 2:
                raise ConfigException, ErrorMessage + ': ' + self.filename
            else:
                raise ConfigException, ErrorMessage



if __name__ == '__main__':

    try:
        cm = ConfigManager('pybot.yaml')
    except ConfigException, e:
        print e
        sys.exit(1)

    print cm.port
    print cm.server

    for ch in cm.channels:
        print ch
        print cm.ops[ch]


    print 'adding new users with channel operator privileges'

    cm.addOp('rovaniemi', 'foo@bar');
    cm.addOp('rovaniemi', 'foo2@bar');
    cm.addOp('rovaniemi', 'foo3@bar');

    cm.addOp('blaa', 'foox3@bar');

    for ch in cm.ops.keys():
        print ch
        print cm.ops[ch]
