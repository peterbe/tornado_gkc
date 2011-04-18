import base64
import time
import re
import hmac
import hashlib
import unittest
from urllib import urlencode
from cStringIO import StringIO

from tornado.httpclient import HTTPRequest
from tornado.testing import LogTrapTestCase, AsyncHTTPTestCase

import app
from apps.main.models import User, UserSettings
from utils.http_test_client import TestClient, HTTPClientMixin


class BaseModelsTestCase(unittest.TestCase):
    _once = False
    def setUp(self):
        if not self._once:
            self._once = True
            from mongokit import Connection
            self.con = Connection()
            self.con.register([User, UserSettings])
            self.db = self.con.test
            self._emptyCollections()

    def _emptyCollections(self):
        [self.db.drop_collection(x) for x
         in self.db.collection_names()
         if x not in ('system.indexes',)]

    def tearDown(self):
        self._emptyCollections()



class BaseHTTPTestCase(AsyncHTTPTestCase, LogTrapTestCase, HTTPClientMixin):

    _once = False
    def setUp(self):
        super(BaseHTTPTestCase, self).setUp()
        if not self._once:
            self._once = True
            self._emptyCollections()

        self._app.settings['email_backend'] = \
          'utils.send_mail.backends.locmem.EmailBackend'
        self._app.settings['email_exceptions'] = False
        self.client = TestClient(self)

    def _emptyCollections(self):
        db = self.db
        [db.drop_collection(x) for x
         in db.collection_names()
         if x not in ('system.indexes',)]

    @property
    def db(self):
        return self._app.con[self._app.database_name]

    def get_db(self):
        print "Deprecated. Use self.db instead"
        return self.db

    def get_app(self):
        return app.Application(database_name='test',
                               xsrf_cookies=False,
                               optimize_static_content=False)

    def decode_cookie_value(self, key, cookie_value):
        try:
            return re.findall('%s=([\w=\|]+);' % key, cookie_value)[0]
        except IndexError:
            raise ValueError("couldn't find %r in %r" % (key, cookie_value))

    def reverse_url(self, *args, **kwargs):
        return self._app.reverse_url(*args, **kwargs)

    def _login(self, username=u'peterbe', email='mail@peterbe.com',
               client=None):
        user = self.db.User.one(dict(username=username))
        if user:
            raise NotImplementedError
        else:
            data = dict(username=username,
                        email=email,
                        first_name="Peter",
                        last_name="Bengtsson")
            user = self.db.User()
            user.username = unicode(username)
            user.email = unicode(email)
            user.first_name = u"Peter"
            user.last_name = u"Bengtsson"
            user.save()
            if client is None:
                client = self.client
            client.cookies['user'] = \
              self.create_signed_value('user', str(user._id))
        user = self.db.User.one(dict(username=username))
        assert user
        return user

    ## these two are shamelessly copied from tornado.web.RequestHandler
    ## because in the _login() we have no access to a request and
    ## we need to be able to set a cookie
    def create_signed_value(self, name, value):
        """Signs and timestamps a string so it cannot be forged.

        Normally used via set_secure_cookie, but provided as a separate
        method for non-cookie uses.  To decode a value not stored
        as a cookie use the optional value argument to get_secure_cookie.
        """
        timestamp = str(int(time.time()))
        value = base64.b64encode(value)
        signature = self._cookie_signature(name, value, timestamp)
        value = "|".join([value, timestamp, signature])
        return value

    def _cookie_signature(self, *parts):
        hash = hmac.new(self._app.settings["cookie_secret"],
                        digestmod=hashlib.sha1)
        for part in parts: hash.update(part)
        return hash.hexdigest()
