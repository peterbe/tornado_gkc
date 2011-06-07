#!/usr/bin/env python
import os, sys
if os.path.abspath(os.curdir) not in sys.path:
    sys.path.insert(0, os.path.abspath(os.curdir))

import tornado.options
from tornado.options import define, options

define("verbose", default=False, help="be louder", type=bool)
define("all", default=False, help="recalculate all users", type=bool)

def main(*args):
    tornado.options.parse_command_line()
    from apps.main.models import User
    from apps.play.models import Play, PlayPoints, PlayedQuestion
    from mongokit import Connection
    con = Connection()
    con.register([Play, User, PlayPoints, PlayedQuestion])
    db = con.gkc
    if options.all:
        max_users = 999999
    else:
        max_users = 10
    finished = (db.Play.find({'finished': {'$ne':None}})
                .sort('finished', -1))
    recent_users = set()
    _broken = False
    for play in finished:
        if _broken:
            break
        for user in play.users:
            recent_users.add(user)
            if len(recent_users) >= max_users:
                _broken = True
                break

    for user in recent_users:
        print user.username
        play_points = PlayPoints.calculate(user)
        #print "\n"
        if options.verbose and not options.all:
            print user.username.ljust(20), play_points.points

    if options.verbose:
        print "Recalculated the points of", len(recent_users), "players"

if __name__ == '__main__':
    import sys
    sys.exit(main(*sys.argv[1:]))
