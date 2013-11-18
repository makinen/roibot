from urllib import urlencode
from urllib2 import urlopen, Request
import re

# There's still a problem with URLs ending in full stops, quotation marks &c,
# but real regexes for URL validation/extraction are really horrible.
# TODO: Match URL only until invalid character occurs ("\' ...)
URL_PATTERN = re.compile(r'(http(s?)://\S+)')
REQUEST_URL = "http://tinyurl.com/api-create.php?"


def get_tinyurl(url):
    """Returns a tinyurl (str) for an URL"""

    params = urlencode([("url", url)])
    req = Request(url="%s%s" % (REQUEST_URL, params))
    f = urlopen(req)

    return f.read().encode('utf-8')

def process_line(bot, channel, user, line):

    if not URL_PATTERN.search(line) or len(line) < 150:
        return

    tinyurls = [get_tinyurl(url[0])
                for url
                in URL_PATTERN.findall(line)]

    bot.sendMessage(channel, user, ", ".join(tinyurls))


if __name__ == '__main__':
    class Printer:
        def sendMessage(*args, **kwargs):
            print args, kwargs

    test_line = "Katso kuvat! http://google.com/" + "0" * 150 +\
            " http://google.com/" + "1" * 30

    process_line(Printer(), None, None, test_line)
