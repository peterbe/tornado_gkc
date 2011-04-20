import base64
from pprint import pprint
from urllib import quote as url_quote
from time import mktime
import re
import datetime
import simplejson as json

from base import BaseHTTPTestCase
from utils import encrypt_password
import utils.send_mail as mail

class HandlersTestCase(BaseHTTPTestCase):

    def test_homepage(self):
        response = self.get('/')

    def test_help_pages(self):
        return
        # index
        response = self.client.get('/help/')
        self.assertEqual(response.code, 200)
        self.assertTrue('Help' in response.body)

        # about
        response = self.client.get('/help/About')
        self.assertEqual(response.code, 200)
        self.assertTrue('Peter Bengtsson' in response.body)

        response = self.client.get('/help/abOUt')
        self.assertEqual(response.code, 200)
        self.assertTrue('Peter Bengtsson' in response.body)

    def test_settings_redirect(self):
        url = self.reverse_url('settings')
        response = self.client.get(url)
        self.assertEqual(response.code, 302)
        self.assertTrue(self.reverse_url('login') in \
          response.headers['location'])
        self.assertTrue(response.headers['location']\
          .endswith('?next=%s' % url_quote(url)))

        # with query string
        response = self.client.get(url, {'name': 'Peter'})
        self.assertEqual(response.code, 302)
        self.assertTrue(self.reverse_url('login') in \
          response.headers['location'])

        self.assertTrue(self.reverse_url('login') in \
          response.headers['location'])

        self.assertTrue('?next=%s' % url_quote(url) in \
          response.headers['location'])

        self.assertTrue(url_quote('?name=Peter') in \
          response.headers['location'])

    def test_change_settings(self):
        url = self.reverse_url('settings')
        response = self.client.get(url)
        self.assertEqual(response.code, 302)
        self.assertTrue(self.reverse_url('login') in \
          response.headers['location'])

        self._login()
        response = self.client.get(url)
        self.assertEqual(response.code, 200)

        fixture_user = self.db.User.one()
        # it should have email, first_name and last_name
        # prefilled in the form
        self.assertTrue('value="%s"' % fixture_user.email \
          in response.body)
        self.assertTrue('value="%s"' % fixture_user.first_name \
          in response.body)
        self.assertTrue('value="%s"' % fixture_user.last_name \
          in response.body)

        # proceed to change something
        data = dict(email="bogus",
                    first_name="Fred")
        response = self.client.post(url, data)
        self.assertEqual(response.code, 400)
        data['email'] = '  ok@test.com \t'
        response = self.client.post(url, data)
        self.assertEqual(response.code, 302)

        response = self.client.get('/')
        self.assertTrue("Fred" in response.body)
        fixture_user = self.db.User.one()
        self.assertEqual(fixture_user.email, 'ok@test.com')
        self.assertEqual(fixture_user.first_name, u'Fred')
        self.assertEqual(fixture_user.last_name, u'')

    def test_facebook_login(self):
        url = self.reverse_url('auth_facebook')
        response = self.client.get(url)
        self.assertEqual(response.code, 302)
        self.assertTrue('facebook.com' in response.headers['location'])
        from apps.main.handlers import FacebookAuthHandler
        FacebookAuthHandler.get_authenticated_user = \
          facebook_get_authenticated_user
        response = self.client.get(url, dict(session='peter'))
        self.assertEqual(response.code, 302)
        settings_url = self.reverse_url('settings')
        self.assertTrue(settings_url in response.headers['location'])

        user = self.db.User.one()
        self.assertEqual(user.username, 'peterbecom')
        self.assertEqual(user.first_name, 'Peter')
        self.assertEqual(user.last_name, 'Bengtsson')
        self.assertTrue(not user.email)

        user_settings = self.db.UserSettings.one({'user.$id': user._id})
        assert user_settings
        self.assertTrue(user_settings.facebook)
        # log out and do it again
        self.client.get(self.reverse_url('logout'))
        response = self.client.get(url, dict(session='peter'))
        self.assertEqual(response.code, 302)
        self.assertTrue(settings_url not in response.headers['location'])
        self.assertEqual(self.db.User.find().count(), 1)

        response = self.client.get('/')
        self.assertTrue('Peter' in response.body)

    def test_facebook_login_no_username(self):
        from apps.main.handlers import FacebookAuthHandler
        FacebookAuthHandler.get_authenticated_user = \
          facebook_get_authenticated_user

        url = self.reverse_url('auth_facebook')
        response = self.client.get(url, dict(session='ashley'))
        self.assertEqual(response.code, 302)
        settings_url = self.reverse_url('settings')
        self.assertTrue(settings_url in response.headers['location'])

        user = self.db.User.one()
        self.assertEqual(user.username, 'ashleynoval')
        self.assertEqual(user.first_name, 'Ashley')
        self.assertEqual(user.last_name, 'Noval')
        self.assertTrue(not user.email)



def facebook_get_authenticated_user(self, callback, **k):
    session = self.get_argument('session')
    if session == 'peter':
        callback({'username': u'peterbecom',
           'pic_square': u'http://profile.ak.fbcdn.net/0000.jpg',
           'first_name': u'Peter',
           'last_name': u'Bengtsson',
           'name': u'Peter Bengtsson',
           'locale': u'en_GB',
           'session_expires': 1303218000,
           'session_key': u'abc123',
           'profile_url': u'http://www.facebook.com/peterbecom',
           'uid': 512720738
        })
    elif session == 'ashley':
        callback({'first_name': u'Ashley',
           'last_name': u'Noval',
           'locale': u'en_US',
           'name': u'Ashley Noval',
           'pic_square': u'http://profile.ak.fbcdn.net/0000.jpg',
           'profile_url': u'http://www.facebook.com/profile.php?id=111111',
           'session_expires': 1303246800,
           'session_key': u'1111113123',
           'uid': 182052646,
           'username': None,
        })
