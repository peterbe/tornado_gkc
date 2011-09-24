#!/usr/bin/env python
#

import site
import os
ROOT = os.path.abspath(os.path.dirname(__file__))
path = lambda *a: os.path.join(ROOT,*a)
site.addsitedir(path('vendor'))

import logging
import time

import tornadio.server
import tornado.options
import settings

from tornado.options import define, options
define("debug", default=False, help="run in debug mode", type=bool)
define("database_name", default=settings.DATABASE_NAME, help="mongodb database name")
define("port", default=8888, help="run on the given port (default 8888)", type=int)
define("flashpolicy", default=None,
           help="location of flashpolicy.xml on port 843 (will require sudo)")
def main():
    for app_name in settings.APPS:
        # import all models so that their MongoKit classes are registered
        __import__('apps.%s' % app_name, globals(), locals(), ['models'], -1)

    tornado.options.parse_command_line()
    from apps.play.client_app import Client, application
    if options.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)
    try:
        tornadio.server.SocketServer(application)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
