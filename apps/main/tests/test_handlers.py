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
