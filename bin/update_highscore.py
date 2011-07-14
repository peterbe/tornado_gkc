#!/usr/bin/env python
import os, sys
p = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if p not in sys.path:
    sys.path.insert(0, p)

import tornado.options
from tornado.options import define, options
import settings

def main(*args):
    tornado.options.parse_command_line()
    from apps.main.models import User, connection
    from apps.play.models import Play, PlayPoints, PlayedQuestion
    db = connection.gkc

    pp = db.PlayPoints.find_random()
    pp.update_highscore_position()


if __name__ == '__main__':
    import sys
    sys.exit(main(*sys.argv[1:]))
