#!/usr/bin/env python
import here

import tornado.options
from tornado.options import define, options

define("verbose", default=False, help="be louder", type=bool)
define("clear_orphans", default=False, help="clear all played question orphans", type=bool)

def main(*args):
    tornado.options.parse_command_line()
    from apps.main.models import User, connection
    from apps.play.models import Play, PlayedQuestion
    from pymongo.objectid import InvalidId, ObjectId
    db = connection.gkc
    unfinished = db.Play.find({'finished': None})
    if options.verbose:
        print unfinished.count(), "unfinished plays"
    for play in unfinished:
        play.delete()

    if options.clear_orphans:
        checked_user_ids = set()
        bad_play_ids = set()
        clear_count = 0
        for play in db.Play.collection.find():
            for user_ref in play['users']:
                if user_ref.id in checked_user_ids:
                    continue
                if db.User.one({'_id': user_ref.id}):
                    checked_user_ids.add(user_ref.id)
                else:
                    bad_play_ids.add(play['_id'])
        for play in db.Play.collection.find({'winner': {'$ne': None}}):
            user_ref = play['winner']
            if user_ref.id in checked_user_ids:
                continue
            if db.User.one({'_id': user_ref.id}):
                checked_user_ids.add(user_ref.id)
            else:
                bad_play_ids.add(play['_id'])
        if bad_play_ids:
            for _id in bad_play_ids:
                db.Play.collection.remove(_id)
            clear_count += len(bad_play_ids)

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


    if options.clear_orphans:
        checked_play_ids = set()
        clear_count = 0
        for played_question in db.PlayedQuestion.collection.find():
            try:
                play_id = played_question['play'].id
                if play_id in checked_play_ids:
                    continue
            except AttributeError:
                play_id = None
            if play_id and db.Play.collection.one({'_id': play_id}):
                checked_play_ids.add(play_id)
            else:
                db.PlayedQuestion.collection.remove(played_question['_id'])
                clear_count += 1
        if options.verbose:
            print clear_count, "played questions cleared"

if __name__ == '__main__':
    import sys
    sys.exit(main(*sys.argv[1:]))
