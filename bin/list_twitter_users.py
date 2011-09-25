#!/usr/bin/env python

"""

LOG IN as kwissle
Then go to:

    https://twitter.com/#!/who_to_follow


"""

import here

import code, re
import tornado.options
from tornado.options import define, options

ALREADY = """
soxcool
ebottabi
Bluebayou1979
oh_cripes
jfremontsmith
ff0000dev
cmholds
sebastianthomas
britainbound
"""

def main():
    tornado.options.parse_command_line()

    from apps.main.models import User, connection, UserSettings
    from apps.play.models import Play
    db = connection.gkc

    already = [x.strip() for x in ALREADY.strip().splitlines()
               if x.strip()]
    for u in db.UserSettings.find().sort('add_date', -1):
        if u['twitter']:
            if u['twitter']['screen_name'] not in already:
                last_played = 'never started'
                for x in (db.Play.collection
                          .find({'users.$id': u.user._id})
                          .sort('started', -1)
                          .limit(1)):
                    if x['finished']:
                        last_played = 'finished %s' % x['finished']
                    else:
                        last_played = 'started %s' % x['started']
                    print u['twitter']['screen_name'].ljust(30), last_played

if __name__ == '__main__':
    main()
