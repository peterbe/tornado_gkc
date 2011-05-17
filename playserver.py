import time

import tornadio.server
import tornado.options
import logging
import settings

from apps.play.client_app import Client, application

def main():
    tornado.options.parse_command_line()
#    application = Application(
#      database_name=options.database_name,
#      debug=options.debug,
#      enabled_protocols=['websocket',
#                         'flashsocket',
#                         'xhr-multipart',
#                         'xhr-polling'
#                         ],
#      flash_policy_port=843,
#      flash_policy_file=op.join(ROOT, 'flashpolicy.xml'),
#      socket_io_port=options.port,
#    )
    logging.getLogger().setLevel(logging.DEBUG)
    try:
        tornadio.server.SocketServer(application)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
