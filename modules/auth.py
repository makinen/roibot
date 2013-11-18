import yaml
import os
from yaml.scanner import ScannerError

def signed_on(bot, bot_nick):

    passwords = None
    try:
        f = open(os.getcwd() + '/modules/auth.yaml')
        try:
            data = f.read()
            passwords = yaml.load(data)
        finally:
            f.close()

    except IOError, ioe:
        bot.logger.error(str(ioe))
        return
    except ScannerError, e:
        bot.logger.error(str(e))
        return

    if bot_nick not in passwords:
        return

    msg = "AUTH "+bot_nick+" " + passwords[bot_nick]

    user = "Q@CServe.quakenet.org"
    bot.sendMessage(None, user, msg)
