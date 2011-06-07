#!/usr/bin/env python
import os, sys
if os.path.abspath(os.curdir) not in sys.path:
    sys.path.insert(0, os.path.abspath(os.curdir))

def main(*args):
    from apps.play.models import Play, PlayedQuestion
    from mongokit import Connection
    con = Connection()
    con.register([Play, PlayedQuestion])
    db = con.gkc
    unfinished = db.Play.find({'finished': None})
    print unfinished.count(), "unfinished plays"
    for play in unfinished:
        play.delete()

    qless_plays = 0
    for play in db.Play.find():
        count = db.PlayedQuestion.find({'play.$id': play._id}).count()
        if count not in (10, 20):
            play.delete()
            qless_plays += 1
    print qless_plays, "plays with not all questions completed"

if __name__ == '__main__':
    import sys
    sys.exit(main(*sys.argv[1:]))
