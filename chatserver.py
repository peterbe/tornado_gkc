import Cookie
import hmac
import base64
import time
import hashlib
import os.path as op
import tornadio.router
import tornadio.server
import tornado.web
from pymongo.objectid import InvalidId, ObjectId
from tornado.options import define, options
import logging
from apps.main.models import User
from mongokit import Connection
import settings

define("database_name", default=settings.DATABASE_NAME, help="mongodb database name")

ROOT = op.normpath(op.dirname(__file__))

class IndexHandler(tornado.web.RequestHandler):
    """Regular HTTP handler to serve the chatroom page"""
    def get(self):
        self.render("index.html")


def _time_independent_equals(a, b):
    if len(a) != len(b):
        return False
    result = 0
    for x, y in zip(a, b):
        result |= ord(x) ^ ord(y)
    return result == 0


class CookieParser(object):
    """hackishly naive"""

    def __init__(self, request):
        self.request = request

    @property
    def cookies(self):
        """A dictionary of Cookie.Morsel objects."""
        if not hasattr(self, "_cookies"):
            self._cookies = Cookie.BaseCookie()
            if "Cookie" in self.request.headers:
                try:
                    self._cookies.load(self.request.headers["Cookie"])
                except:
                    self.clear_all_cookies()
        return self._cookies

    def get_cookie(self, name, default=None):
        """Gets the value of the cookie with the given name, else default."""
        if name in self.cookies:
            return self.cookies[name].value
        return default


    def get_secure_cookie(self, name, include_name=True, value=None):
        """Returns the given signed cookie if it validates, or None.

        In older versions of Tornado (0.1 and 0.2), we did not include the
        name of the cookie in the cookie signature. To read these old-style
        cookies, pass include_name=False to this method. Otherwise, all
        attempts to read old-style cookies will fail (and you may log all
        your users out whose cookies were written with a previous Tornado
        version).
        """
        if value is None:
            value = self.get_cookie(name)
        if not value: return None
        parts = value.split("|")

        if len(parts) != 3: return None
        if include_name:
            signature = self._cookie_signature(name, parts[0], parts[1])
        else:
            signature = self._cookie_signature(parts[0], parts[1])
        if not _time_independent_equals(parts[2], signature):
            logging.warning("Invalid cookie signature %r", value)
            return None
        timestamp = int(parts[1])
        if timestamp < time.time() - 31 * 86400:
            logging.warning("Expired cookie %r", value)
            return None
        if timestamp > time.time() + 31 * 86400:
            # _cookie_signature does not hash a delimiter between the
            # parts of the cookie, so an attacker could transfer trailing
            # digits from the payload to the timestamp without altering the
            # signature.  For backwards compatibility, sanity-check timestamp
            # here instead of modifying _cookie_signature.
            logging.warning("Cookie timestamp in future; possible tampering %r", value)
            return None
        if parts[1].startswith("0"):
            logging.warning("Tampered cookie %r", value)
        try:
            return base64.b64decode(parts[0])
        except:
            return None

    def _cookie_signature(self, *parts):
        hash = hmac.new(settings.COOKIE_SECRET, digestmod=hashlib.sha1)
        for part in parts: hash.update(part)
        return hash.hexdigest()


class ChatConnection(tornadio.SocketConnection):
    # Class level variable
    participants = set()

    def on_open(self, request, **kwargs):
        cookie_parser = CookieParser(request)
        user_id = cookie_parser.get_secure_cookie('user')

        user = application.db.User.one({'_id': ObjectId(user_id)})
        self.user_id = user_id
        self.user_name = user.first_name and user.first_name or user.username
        self.participants.add(self)
        self.send({'m':"Welcome! %s" % self.user_name})

    def on_message(self, message):
        for p in self.participants:
            p.send({'m': message, 'u': self.user_name})

    def on_close(self):
        try:
            self.participants.remove(self)
            message = "%s has left" % self.user_name
            for p in self.participants:
                p.send({'m': message})
        except KeyError:
            pass

#use the routes classmethod to build the correct resource
ChatRouter = tornadio.get_router(ChatConnection)

class Application(tornado.web.Application):
    def __init__(self, handlers, database_name=None, **kwargs):
        tornado.web.Application.__init__(self, handlers, **kwargs)
        self.database_name = database_name and database_name or options.database_name
        self.con = Connection()
        self.con.register([User])

    @property
    def db(self):
        return self.con[self.database_name]

#configure the Tornado application
application = Application(
    [(r"/", IndexHandler), ChatRouter.route()],
    enabled_protocols=['websocket',
                       'flashsocket',
                       'xhr-multipart',
                       'xhr-polling'],
    flash_policy_port=843,
    flash_policy_file=op.join(ROOT, 'flashpolicy.xml'),
    socket_io_port=8001,
)

if __name__ == "__main__":
    logging.getLogger().setLevel(logging.DEBUG)
    try:
        tornadio.server.SocketServer(application)
    except KeyboardInterrupt:
        pass