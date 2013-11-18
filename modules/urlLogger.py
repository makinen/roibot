#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Main idea for this module is to make file where are all URLs bot has seen
# in specific channel. Because this is mostly boring, there is a feature that
# bot yells if URL is already seen in that channel.
#
# Module made by Erkki-Juhani Lämsä

import re, os, sys

url_regexp = re.compile('.*http(s?)://')

def process_line(bot, channel, user, line):
    if url_regexp.match(line):
        url = line[line.find('http'):].split()[0]
    else:
        return
    u = User(user)

    # if file doesn't exist, open() will create it, that's why existence wasn't
    # checked, though it can be unwritable or folder can be unacessable
    try:
    #if 1:
        f = open(os.getcwd() + '/modules/urlz_' + channel + '.log', 'a+')
        s = f.read()
        l = s.split('\n')
        message = ''
        for i in l:
            if url == i:
                message = u.nick + ': That link is ancient!'
    
        if message == '':
            f.write(url + '\n')
            f.close()
            return
        f.close()
        if url == 'http://www.v2.fi/images/entertainment/articles/341/pic5.jpg':
            message = u.nick + ': WANHA!! Ei toi sulle anna koskaan.'
        #print message
        bot.sendMessage(channel, user, message)
    except IOError, ioe:
        bot.logger.error(str(ioe))
        bot.sendMessage(channel, user, 'I has IOError')

class User:
    def __init__(self, user):
        l = [user.split('!')[0]] + user.split('!')[1].split('@')
        self.nick, self.ident, self.hostname = l[0], l[1], l[2] 
