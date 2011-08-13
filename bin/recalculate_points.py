#!/usr/bin/env python
import os, sys
p = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if p not in sys.path:
    sys.path.insert(0, p)

import tornado.options
from tornado.options import define, options
import settings

define("verbose", default=False, help="be louder", type=bool)
define("all", default=False, help="recalculate all users", type=bool)
define("users", default=10, help="no. recent plays", type=int)
define("random", default=False, help="pick random users", type=bool)

def main(*args):
    tornado.options.parse_command_line()
    from apps.main.models import User, connection
    from apps.play.models import PlayPoints
    import apps.rules.models
    db = connection.gkc
    if options.all:
        max_users = 999999
    else:
        max_users = options.users

    recent_users = []
    if options.random:
        while len(recent_users) < max_users:
            play = db.Play.find_random()
            if play.finished:
                for user in play.users:
                    if user.anonymous:
                        continue
                    if user not in recent_users:
                        recent_users.append(user)

    else:
        finished = (db.Play.find({'finished': {'$ne':None}})
                    .sort('finished', -1))
        _broken = False
        for play in finished:
            if _broken:
                break
            for user in play.users:
                if user.anonymous:
                    continue
                if user not in recent_users:
                    recent_users.append(user)
                if len(recent_users) >= max_users:
                    _broken = True
                    break
    computer = (db.User.collection
          .one({'username': settings.COMPUTER_USERNAME}))

    default_rules_id = db.Rules.one({'default': True})._id

    _rule_names = {}
    def get_rule_name(rule_id):
        if rule_id not in _rule_names:
            r = db.Rules.collection.one({'_id': rule_id})
            _rule_names[rule_id] = r['name']
        return _rule_names[rule_id]

    for user in recent_users:
        if computer and user._id == computer['_id']:
            continue
        played_rules_ids = [default_rules_id]
        for p in db.Play.collection.find({'users.$id': user['_id'],
                                               'rules': {'$ne': default_rules_id}}):
            p_rules_id = p['rules']  # nb. not using the 'rules' proper in Play
            if p_rules_id not in played_rules_ids:
                played_rules_ids.append(p_rules_id)

        assert len(played_rules_ids) == len(set(played_rules_ids))
        for rule_id in played_rules_ids:
            play_points = PlayPoints.calculate(user, rule_id)
            if options.verbose and not options.all:
                print user.username.ljust(20),
                print get_rule_name(rule_id).ljust(50),
                print play_points.points

    if options.verbose:
        print "Recalculated the points of", len(recent_users), "players"

if __name__ == '__main__':
    import sys
    sys.exit(main(*sys.argv[1:]))
