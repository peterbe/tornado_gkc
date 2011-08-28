#!/usr/bin/env python
import os, sys
p = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if p not in sys.path:
    sys.path.insert(0, p)

import datetime
from urllib import urlopen
import tornado.options
from tornado.options import define, options
import settings

define("verbose", default=False, help="be louder", type=bool)
define("all", default=False, help="recalculate all users", type=bool)
define("users", default=10, help="no. recent plays", type=int)
define("domain", default="kwissle.com", help="domain name", type=str)

def main(*args):
    tornado.options.parse_command_line()
    from apps.main.models import User, connection
    from apps.newsletter.models import NewsletterSettings
    import apps.rules.models
    db = connection.gkc
    if options.all:
        max_users = 999999
    else:
        max_users = options.users

    now = datetime.datetime.utcnow()
    to_send = (db.NewsletterSettings
               .find({'next_send': {'$lt': now}})
               .limit(max_users)
               .sort('next_send'))

    base_url = 'http://%s' % options.domain
    for each in to_send:
        user = db.User.collection.one({'_id': each.user},
                                      fields=('email', 'username'))

        if not user['email']:
            if options.verbose:
                print "Skipping %r because no email" % user['username']
            continue

        if user['email'] not in ('peterbe@gmail.com',
                                 'mail@peterbe.com',
                                 'ashleynoval@gmail.com',
                                 'abbas@abbashalai.com',
                                 'sguidi@gmail.com',
                                 'westc25@gmail.com',
                                 ):
            print "\tIN ALPHA TESTING MODE ONLY SENDING TO SOME"
            print "\tSkipping:", user['email']
            continue

        url = base_url + '/newsletter/%s/send/' % each.user
        if options.verbose:
            print "SENDING TO %s" % user['email']
            url += '?verbose=true'
            print url


        result = urlopen(url).read()
        if options.verbose:
            print '- ' * 40
            print result
            print '-' * 80



if __name__ == '__main__':
    import sys
    sys.exit(main(*sys.argv[1:]))
