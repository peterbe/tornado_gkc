#!/usr/bin/env python
import os, sys
p = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if p not in sys.path:
    sys.path.insert(0, p)

import tornado.options
from tornado.options import define, options

define("verbose", default=False, help="be louder", type=bool)
define("clear_orphans", default=False, help="clear all played question orphans", type=bool)

def main(*args):
    tornado.options.parse_command_line()
    from apps.play.models import Play, PlayedQuestion
    from mongokit import Connection
    con = Connection()
    con.register([Play, PlayedQuestion])
    db = con.gkc
    unfinished = db.Play.find({'finished': None})
    if options.verbose:
        print unfinished.count(), "unfinished plays"
    for play in unfinished:
        play.delete()

    qless_plays = 0
    for play in db.Play.find():
        count = db.PlayedQuestion.find({'play.$id': play._id}).count()
        if count not in (10, 20):
            for qp in db.PlayedQuestion.find({'play.$id': play._id}):
                qp.delete()
            play.delete()
            qless_plays += 1
    if options.verbose:
        print qless_plays, "plays with not all questions completed"

    from pymongo.objectid import InvalidId, ObjectId
    if options.clear_orphans:
        checked_play_ids = set()
        clear_count = 0
        for played_question in db.PlayedQuestion.collection.find():
            play_id = played_question['play'].id
            if play_id in checked_play_ids:
                continue
            if db.Play.collection.one({'_id': play_id}):
                checked_play_ids.add(play_id)
            else:
                db.PlayedQuestion.collection.remove(played_question['_id'])
                clear_count += 1
        if options.verbose:
            print clear_count, "played questions cleared"

if __name__ == '__main__':
    import sys
    sys.exit(main(*sys.argv[1:]))
