from BeautifulSoup import BeautifulSoup
from BeautifulSoup import BeautifulStoneSoup
import locale
import urllib
import urlparse
import time
import re

url_regexp = re.compile('.*http(s?)://')
url_cache = []

def get_url(url):
    htmlfile = urllib.urlopen(url)
    # TODO check size
    doc = htmlfile.readlines()
    htmlfile.close()
    bs = BeautifulSoup("".join(doc), convertEntities=BeautifulStoneSoup.HTML_ENTITIES)
    return bs

def process_line(bot, channel, user, line):

    print ">>>> channel: " + str(channel)
    print ">>>> user: " + str(user)

    if url_regexp.match(line):
        url = line[line.find('http'):].split()[0]
    else:
        return

    print ">>> let's find out the title"

    if url.find("youtube") != -1:
        title = "Title: " + youtube(url)
        title = title.encode('utf-8')
        bot.sendMessage(channel, user, title)
        return

    bs = get_url(url)
    if not bs: return

    title = ""


    if url.startswith("http://www.en.wikipedia.org") or \
	url.startswith("http://www.fi.wikipedia.org") or \
        url.startswith("http://fi.wikipedia.org") or \
        url.startswith("http://en.wikipedia.org") or \
        url.startswith("http://www.wikipedia.org"): return


    # TODO imdb breaks this
    title = bs.html.head.title.contents[0]
    print ">> title: " + title

    # cache the title
    global url_cache
    if title in url_cache:
        return
    if url_cache and len(url_cache) > 5:
        url_cache = url_cache[::-1]
        url_cache.pop()
        url_cache = url_cache[::-1]

    url_cache.append(title)

    # no title attribute
    if not title: return

    url = urllib.unquote(url.encode("utf-8"))

    hostname = urlparse.urlparse(url.lower()).netloc
    #Remove the 'user:passw', 'www.' and ':port' parts
    hostname = ".".join(hostname.split('@')[-1].split(':')[0].lstrip('www.').split('.'))

    #remove the hostname from the fetched title
    cmptitle = title.lower().strip()
    for part in hostname.split('.'):
        idx = cmptitle.replace(' ', '').find(part)
        if idx != -1:
            break

    print ">> cmptitle: " + cmptitle

    if idx > len(title)/2:
        cmptitle = title[0:idx+(len(title[0:idx])-len(title[0:idx].replace(' ', '')))].strip()
    elif idx == 0:
        cmptitle = title[idx+len(hostname):].strip()

    url_parts = url.replace('-', ' ').replace('+', ' ').replace('_', ' ').rsplit('/')

    d = []
    for part in url_parts:
        if part.rfind('.') != -1:
            part = part[:part.rfind('.')]
        d.append(levenshtein_distance(part.lower(), cmptitle.lower()))

    print "cmptitle: " + cmptitle
    print "distance: " + str(min(d))
    print "title length: %d" % len(title)
    print "url: " + url
    if len(title) < 20 and min(d) < 5:
        return
    elif len(title) >= 20 and len(title) <= 30 and min(d) < 10:
        return
    elif len(title) > 30 and len(title) <= 60 and min(d) <= 21:
        return
    elif len(title) > 60 and min(d) < 37:
        return

    title = "Title: " + remove_spaces(title)
    
#

   # elif url.startswith("http://www.iltalehti.fi"):
   #     # the last part is the actual title
   #     title = bs.html.head.title.contents[0]
   #     title = "Title: Iltalehti - " + title.split("|")[-1].strip()


    #encode the python unicode string into the original encoding
    #title = title.encode(bs.originalEncoding)
    title = title.encode('utf-8')

    try:
        bot.sendMessage(channel, user, title)
    # title tag is empty
    except AttributeError:
        pass

def levenshtein_distance(s, t):

    d = [ [i] + [0]*len(t) for i in xrange(0, len(s)+1) ]
    d[0] = [i for i in xrange(0, (len(t)+1))]

    for i in xrange(1, len(d)):
        for j in xrange(1, len(d[i])):
            if len(s) > i-1 and len(t) > j-1 and s[i-1] == t[j-1]:
                d[i][j] = d[i-1][j-1]
            else:
                d[i][j] = min((d[i-1][j]+1, d[i][j-1]+1, d[i-1][j-1]+1))

    return d[len(s)][len(t)]

# This function takes string inside and removes lines of multiple spaces from it
# It is made basically because of html titles in youtube.com are in many lines with 
# lots of spaces.
# Basically it changes '    ' to ' '.

def remove_spaces(s):
    s = s.strip().replace('\n', '').replace('\r', '').replace('\t', '')
    l = list(s)
    j = ' ' #if you want to remove multiple other things to just one, change this to something else
    p = ''
    n = 0
    for i in l:
        if i == j and i == p:
            l[n] = ''
        elif i == j and i != p:
            p = i
        else:
            p = ''
        n = n + 1
    s = "".join(l)
    return s

# Stolen from pyfibot. Made by Shrike.
def youtube(url):
    """http://*youtube.com/watch?*v=*"""
    gdata_url = "http://gdata.youtube.com/feeds/api/videos/%s"
    
    match = re.match("http://.*?youtube.com/watch\?.*?v=([^&]+)", url)
    if match:
        infourl = gdata_url % match.group(1)
        bs = get_url(infourl)
        if not bs: return
    
        entry = bs.first("entry")

        if not entry: 
            log.info("Video too recent, no info through API yet.")
            return

        author = entry.author.next.string
        # if an entry doesn't have a rating, the whole element is missing
        try:
            rating = float(entry.first("gd:rating")['average'])
        except TypeError:
            rating = 0.0

        stars = int(round(rating)) * "*"
            
        statistics = entry.first("yt:statistics")
        if statistics:
            views = statistics['viewcount']
        else:
            views = "no"

        racy = entry.first("yt:racy")

        media = entry.first("media:group")
        title = media.first("media:title").string
        secs = media.first("yt:duration") and int(media.first("yt:duration")['seconds']) or -1

        lengthstr = []
        hours,minutes,seconds = secs//3600,secs//60%60,secs%60

        if hours > 0: lengthstr.append("%dh" % hours)
        if minutes > 0: lengthstr.append("%dm" % minutes)
        if seconds > 0: lengthstr.append("%ds" % seconds)

        if racy:
            adult = " - XXX"
        else:
            adult = ""
        
        return "%s by %s [%s - %s - %s views%s]" % (title, author, "".join(lengthstr), "[%-5s]" % stars, views, adult)


