import base64
from pprint import pprint
from time import mktime
import re
import datetime
import simplejson as json

from base import BaseHTTPTestCase
from utils import encrypt_password
#from apps.main.models import Event, User, Share
import utils.send_mail as mail
from apps.main.config import MINIMUM_DAY_SECONDS

class ApplicationTestCase(BaseHTTPTestCase):

    def test_homepage(self):
        response = self.get('/')
        self.assertTrue('id="calendar"' in response.body)

    def test_user_settings(self):
        response = self.get('/user/settings/')
        self.assertEqual(response.code, 200)
        # nothing is checked
        self.assertTrue(not response.body.count('checked'))
        self.assertTrue('name="hide_weekend"' in response.body)
        self.assertTrue('name="monday_first"' in response.body)
        self.assertTrue('name="disable_sound"' in response.body)

        response = self.get('/user/settings.js')
        self.assertEqual(response.code, 200)
        json_str = re.findall('{.*?}', response.body)[0]
        settings = json.loads(json_str)
        self.assertEqual(settings['hide_weekend'], False)
        self.assertEqual(settings['monday_first'], False)

        data = {'hide_weekend':True,
                'disable_sound':True,
                'first_hour':10}
        response = self.post('/user/settings/', data, follow_redirects=False)
        self.assertEqual(response.code, 302)
        guid_cookie = self.decode_cookie_value('guid', response.headers['Set-Cookie'])
        guid = base64.b64decode(guid_cookie.split('|')[0])

        db = self.get_db()
        user = db.User.one(dict(guid=guid))
        user_settings = db.UserSettings.one({
          'user.$id': user._id
        })
        self.assertTrue(user_settings.hide_weekend)
        self.assertTrue(user_settings.disable_sound)
        self.assertEqual(user_settings.first_hour, 10)
        self.assertFalse(user_settings.monday_first)

    def test_signup(self):
        # the get method is just used to validate if an email is used another
        # user
        response = self.get('/user/signup/')
        self.assertEqual(response.code, 404)

        data = {'validate_email': 'peter@test.com'}
        response = self.get('/user/signup/', data)
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct, dict(ok=True))

        user = self.get_db().users.User()
        user.email = u"Peter@Test.com"
        user.save()

        data = {'validate_email': 'peter@test.com'}
        response = self.get('/user/signup/', data)
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct, dict(error='taken'))

        data = dict(email="peterbe@gmail.com",
                    password="secret",
                    first_name="Peter",
                    last_name="Bengtsson")
        response = self.post('/user/signup/', data, follow_redirects=False)
        self.assertEqual(response.code, 302)

        data.pop('password')
        user = self.get_db().users.User.one(data)
        self.assertTrue(user)

        # a secure cookie would have been set containing the user id
        user_cookie = self.decode_cookie_value('user', response.headers['Set-Cookie'])
        guid = base64.b64decode(user_cookie.split('|')[0])
        self.assertEqual(user.guid, guid)

    def test_change_account(self):
        db = self.get_db()

        user = db.User()
        user.email = u"peter@fry-it.com"
        user.first_name = u"Ptr"
        user.password = encrypt_password(u"secret")
        user.save()

        other_user = db.User()
        other_user.email = u'peterbe@gmail.com'
        other_user.save()

        data = dict(email=user.email, password="secret")
        response = self.post('/auth/login/', data, follow_redirects=False)
        self.assertEqual(response.code, 302)
        user_cookie = self.decode_cookie_value('user', response.headers['Set-Cookie'])
        guid = base64.b64decode(user_cookie.split('|')[0])
        self.assertEqual(user.guid, guid)
        cookie = 'user=%s;' % user_cookie

        response = self.get('/user/account/', headers={'Cookie':cookie})
        self.assertEqual(response.code, 200)
        self.assertTrue('value="Ptr"' in response.body)

        # not logged in
        response = self.post('/user/account/', {})
        self.assertEqual(response.code, 403)

        # no email supplied
        response = self.post('/user/account/', {}, headers={'Cookie':cookie})
        self.assertEqual(response.code, 404)

        data = {'email':'bob'}
        response = self.post('/user/account/', data, headers={'Cookie':cookie})
        self.assertEqual(response.code, 400)

        data = {'email':'PETERBE@gmail.com'}
        response = self.post('/user/account/', data, headers={'Cookie':cookie})
        self.assertEqual(response.code, 400)

        data = {'email':'bob@test.com', 'last_name': '  Last Name \n'}
        response = self.post('/user/account/', data, headers={'Cookie':cookie},
                             follow_redirects=False)
        self.assertEqual(response.code, 302)

        user = db.User.one(dict(email='bob@test.com'))
        self.assertEqual(user.last_name, data['last_name'].strip())

        # log out
        response = self.get('/auth/logout/', headers={'Cookie':cookie},
                            follow_redirects=False)
        self.assertEqual(response.code, 302)
        self.assertTrue('user=;' in response.headers['Set-Cookie'])


    def test_help_pages(self):
        # index
        response = self.get('/help/')
        self.assertEqual(response.code, 200)
        self.assertTrue('Help' in response.body)

        # about
        response = self.get('/help/About')
        self.assertEqual(response.code, 200)
        self.assertTrue('Peter Bengtsson' in response.body)

        response = self.get('/help/abOUt')
        self.assertEqual(response.code, 200)
        self.assertTrue('Peter Bengtsson' in response.body)

        # Bookmarklet
        response = self.get('/help/Bookmarklet')
        self.assertEqual(response.code, 200)
        self.assertTrue('Bookmarklet' in response.body)

        # API
        response = self.get('/help/API')
        self.assertEqual(response.code, 200)
        self.assertTrue('API' in response.body)

        # start using the app and the API page will be different
        today = datetime.date.today()
        data = {'title': "Foo",
                'date': mktime(today.timetuple()),
                'all_day': 'yes'}
        response = self.post('/events/', data)
        self.assertEqual(response.code, 200)
        guid_cookie = self.decode_cookie_value('guid', response.headers['Set-Cookie'])
        cookie = 'guid=%s;' % guid_cookie
        guid = base64.b64decode(guid_cookie.split('|')[0])

        response = self.get('/help/API', headers={'Cookie':cookie})
        self.assertEqual(response.code, 200)
        self.assertTrue(guid in response.body)
        self.assertTrue(response.body.split('<body')[1].count('https://') == 0)

        # now log in as a wealthy premium user
        db = self.get_db()
        user = db.User()
        user.email = u"test@test.com"
        user.premium = True
        user.set_password('secret')
        user.save()

        data = dict(email=user.email, password="secret")
        response = self.post('/auth/login/', data, follow_redirects=False)
        self.assertEqual(response.code, 302)
        user_cookie = self.decode_cookie_value('user', response.headers['Set-Cookie'])
        cookie = 'user=%s;' % user_cookie
        response = self.get('/help/API', headers={'Cookie':cookie})
        self.assertEqual(response.code, 200)
        self.assertTrue(response.body.count('https://') >= 1)


    def test_reset_password(self):
        # sign up first
        data = dict(email="peterbe@gmail.com",
                    password="secret",
                    first_name="Peter",
                    last_name="Bengtsson")
        response = self.post('/user/signup/', data, follow_redirects=False)
        self.assertEqual(response.code, 302)

        data.pop('password')
        user = self.get_db().users.User.one(data)
        self.assertTrue(user)


        response = self.get('/user/forgotten/')
        self.assertEqual(response.code, 200)

        response = self.post('/user/forgotten/', dict(email="bogus"))
        self.assertEqual(response.code, 400)

        response = self.post('/user/forgotten/', dict(email="valid@email.com"))
        self.assertEqual(response.code, 200)
        self.assertTrue('Error' in response.body)
        self.assertTrue('valid@email.com' in response.body)

        response = self.post('/user/forgotten/', dict(email="PETERBE@gmail.com"))
        self.assertEqual(response.code, 200)
        self.assertTrue('success' in response.body)
        self.assertTrue('peterbe@gmail.com' in response.body)

        sent_email = mail.outbox[-1]
        self.assertTrue('peterbe@gmail.com' in sent_email.to)

        links = [x.strip() for x in sent_email.body.split()
                 if x.strip().startswith('http')]
        from urlparse import urlparse
        link = [x for x in links if x.count('recover')][0]
        # pretending to click the link in the email now
        url = urlparse(link).path
        response = self.get(url)
        self.assertEqual(response.code, 200)

        self.assertTrue('name="password"' in response.body)

        data = dict(password='secret')

        response = self.post(url, data, follow_redirects=False)
        self.assertEqual(response.code, 302)

        user_cookie = self.decode_cookie_value('user', response.headers['Set-Cookie'])
        guid = base64.b64decode(user_cookie.split('|')[0])
        self.assertEqual(user.guid, guid)
        cookie = 'user=%s;' % user_cookie

        response = self.get('/', headers={'Cookie': cookie})
        self.assertTrue("Peter" in response.body)


    def test_change_settings_without_logging_in(self):
        # without even posting something, change your settings
        db = self.get_db()
        assert not db.UserSettings.find().count()

        data = dict(disable_sound=True, monday_first=True)
        # special client side trick
        data['anchor'] = '#month,2010,11,1'

        response = self.post('/user/settings/', data, follow_redirects=False)
        self.assertEqual(response.code, 302)
        self.assertTrue(response.headers['Location'].endswith(data['anchor']))

        guid_cookie = self.decode_cookie_value('guid', response.headers['Set-Cookie'])
        cookie = 'guid=%s;' % guid_cookie
        guid = base64.b64decode(guid_cookie.split('|')[0])

        self.assertEqual(db.User.find({'guid':guid}).count(), 1)
        user = db.User.one({'guid':guid})
        self.assertEqual(db.UserSettings.find({'user.$id':user._id}).count(), 1)

        # pick up the cookie and continue to the home page
        response = self.get(response.headers['Location'], headers={'Cookie': cookie})
        self.assertEqual(response.code, 200)
        # the settings we just made will be encoded as a JSON string inside the HTML
        self.assertTrue('"monday_first": true' in response.body)
