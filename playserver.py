import time

import tornadio.server
import tornado.options
import logging
import settings


from tornado.options import define
def main():
    tornado.options.parse_command_line()

    define("debug", default=False, help="run in debug mode", type=bool)
    define("database_name", default=settings.DATABASE_NAME, help="mongodb database name")
    define("port", default=8888, help="run on the given port", type=int)
    from apps.play.client_app import Client, application

    logging.getLogger().setLevel(logging.DEBUG)
    try:
        tornadio.server.SocketServer(application)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
