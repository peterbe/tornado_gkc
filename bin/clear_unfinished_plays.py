#!/usr/bin/env python
import os, sys
if os.path.abspath(os.curdir) not in sys.path:
    sys.path.insert(0, os.path.abspath(os.curdir))

def main(*args):
    from apps.play.models import Play
    from mongokit import Connection
    con = Connection()
    con.register([Play])
    db = con.gkc
    unfinished = db.Play.find({'finished': None})
    print unfinished.count(), "unfinished plays"
    for play in unfinished:
        play.delete()

if __name__ == '__main__':
    import sys
    sys.exit(main(*sys.argv[1:]))
