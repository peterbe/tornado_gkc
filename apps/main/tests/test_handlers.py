import os
import mimetypes
from pprint import pprint
from urllib import quote as url_quote
from time import mktime
from urlparse import urlparse
import re
import datetime
import simplejson as json

import settings
from base import BaseHTTPTestCase
from tornado_utils import encrypt_password
from utils import get_question_slug_url
import tornado_utils.send_mail as mail


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

    def test_login_page(self):
        url = self.reverse_url('login')
        response = self.client.get(url)
        self.assertEqual(response.code, 200)

    def test_google_login(self):
        url = self.reverse_url('auth_google')
        response = self.client.get(url)
        self.assertEqual(response.code, 302)
        self.assertTrue('google.com' in response.headers['location'])

        from apps.main.handlers import GoogleAuthHandler
        GoogleAuthHandler.get_authenticated_user = \
          google_get_authenticated_user
        response = self.client.get(url, {'openid.mode':'xxx'})
        self.assertEqual(response.code, 302)

        user = self.db.User.one()
        self.assertEqual(user.username, 'peterbe')
        self.assertEqual(user.first_name, 'Peter')
        self.assertEqual(user.last_name, None)
        self.assertTrue(user.email)

        user_settings = self.db.UserSettings.one()
        self.assertEqual(user_settings.email_verified, user.email)

    def test_twitter_login(self):
        from apps.main.handlers import TwitterAuthHandler
        TwitterAuthHandler.get_authenticated_user = \
          twitter_get_authenticated_user
        TwitterAuthHandler.authenticate_redirect = \
          twitter_authenticate_redirect
        url = self.reverse_url('auth_twitter')
        response = self.client.get(url)
        self.assertEqual(response.code, 302)
        self.assertTrue('twitter.com' in response.headers['location'])

        response = self.client.get(url, {'oauth_token':'xxx'})
        self.assertEqual(response.code, 302)

        user = self.db.User.one()
        self.assertEqual(user.username, 'peterbe')
        self.assertEqual(user.first_name, 'Peter Bengtsson')
        self.assertEqual(user.last_name, None)
        self.assertTrue(not user.email)

        user_settings = self.db.UserSettings.one()
        self.assertEqual(user_settings.email_verified, None)

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

        user_settings = self.db.UserSettings.one({'user': user._id})
        assert user_settings
        self.assertTrue(user_settings.facebook)
        self.assertEqual(user_settings.email_verified, None)

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

    def test_toggle_user_settings(self):
        url = self.reverse_url('user_settings_toggle')
        response = self.client.get(url, {'sound':'anything'})
        self.assertEqual(response.code, 405)
        response = self.client.post(url, {'sound':'anything'})
        self.assertEqual(response.code, 403)
        self._login()
        response = self.client.post(url, {'stuff':'anything'})
        self.assertEqual(response.code, 400)
        response = self.client.post(url, {'sound':'anything'})
        self.assertEqual(response.code, 200)
        user_settings = self.db.UserSettings.one()
        self.assertTrue(user_settings.disable_sound)
        response = self.client.post(url, {'sound':'anything'})
        self.assertEqual(response.code, 200)
        user_settings = self.db.UserSettings.one()
        self.assertTrue(not user_settings.disable_sound)


    def test_authenticated_decorator_redirect(self):
        # if you anonymously click on a link you need to be logged in
        # to it should redirect you to the login page
        login_url = self.reverse_url('login')
        assert self.client.get(login_url).code == 200

        url = self.reverse_url('questions')
        response = self.client.get(url)
        self.assertEqual(response.code, 302)
        parsed = urlparse(response.headers['location'])
        self.assertEqual(parsed.path,
                         login_url)
        self.assertEqual(parsed.query,
                         'next=%s' % url_quote(url, safe=''))

    def test_anonymous_to_logged_in_after_play(self):
        url = self.reverse_url('start_play')
        response = self.client.get(url)
        self.assertEqual(response.code, 302)
        user = self.db.User.one()
        self.assertTrue(user.anonymous)

        bob = self.db.User()
        bob.username = u'bob'
        bob.save()

        play = self.db.Play()
        play.users = [user, bob]
        play.rules = self.default_rules_id
        play.no_players = 2
        play.no_questions = 2
        play.started = datetime.datetime.now()
        play.save()

        q1 = self._create_question()
        q2 = self._create_question()

        # 3 point
        pq1a = self.db.PlayedQuestion()
        pq1a.play = play
        pq1a.question = q1
        pq1a.user = user
        pq1a.answer = u'yes'
        pq1a.alternatives = False
        pq1a.right = True
        pq1a.save()

        # 0 points
        pq1b = self.db.PlayedQuestion()
        pq1b.play = play
        pq1b.question = q1
        pq1b.user = bob
        pq1b.answer = u'wrong'
        pq1b.alternatives = True
        pq1b.right = False
        pq1b.save()

        # 0 points
        pq2a = self.db.PlayedQuestion()
        pq2a.play = play
        pq2a.question = q2
        pq2a.user = user
        pq2a.answer = u'wrong'
        pq2a.right = False
        pq2a.save()

        # 1 point
        pq2b = self.db.PlayedQuestion()
        pq2b.play = play
        pq2b.question = q2
        pq2b.user = bob
        pq2b.answer = u'yes'
        pq2b.alternatives = True
        pq2b.right = True
        pq2b.save()

        play.winner = user
        play.finished = datetime.datetime.now()
        play.save()

        from apps.play.models import PlayPoints
        play_points_user = PlayPoints.calculate(user, self.default_rules_id)
        self.assertEqual(play_points_user.draws, 0)
        self.assertEqual(play_points_user.wins, 1)
        self.assertEqual(play_points_user.losses, 0)
        self.assertEqual(play_points_user.points, 3)

        play_points_bob = PlayPoints.calculate(bob, self.default_rules_id)
        self.assertEqual(play_points_bob.draws, 0)
        self.assertEqual(play_points_bob.wins, 0)
        self.assertEqual(play_points_bob.losses, 1)
        self.assertEqual(play_points_bob.points, 1)

        # lastly, both people send each other a message
        msg1 = self.db.PlayMessage()
        msg1.play = play
        msg1['from'] = user
        msg1.to = bob
        msg1.message = u'Well done'
        msg1.save()

        msg2 = self.db.PlayMessage()
        msg2.play = play
        msg2['from'] = bob
        msg2.to = user
        msg2.message = u'Thanks'
        msg2.save()

        url = self.reverse_url('login')
        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        self.assertTrue('3 Kwissle points' in response.body)

        from apps.main.handlers import TwitterAuthHandler
        TwitterAuthHandler.get_authenticated_user = \
          twitter_get_authenticated_user
        TwitterAuthHandler.authenticate_redirect = \
          twitter_authenticate_redirect
        url = self.reverse_url('auth_twitter')
        response = self.client.get(url)
        self.assertEqual(response.code, 302)
        self.assertTrue('twitter.com' in response.headers['location'])

        response = self.client.get(url, {'oauth_token':'xxx'})
        self.assertEqual(response.code, 302)

        peterbe = self.db.User.one({'username': 'peterbe'})
        self.assertTrue(peterbe)

        self.assertEqual(self.db.User.find().count(), 2)
        self.assertEqual(self.db.PlayedQuestion.find({'user.$id': peterbe._id}).count(), 2)
        self.assertEqual(self.db.PlayPoints.find({'user.$id': peterbe._id}).count(), 1)
        self.assertEqual(self.db.Play.find({'users.$id': peterbe._id}).count(), 1)
        self.assertEqual(self.db.Play.find({'winner.$id': peterbe._id}).count(), 1)
        self.assertEqual(self.db.PlayMessage.find({'from.$id': peterbe._id}).count(), 1)
        self.assertEqual(self.db.PlayMessage.find({'to.$id': peterbe._id}).count(), 1)


    def _create_question(self,
                         text=None,
                         answer=u'yes',
                         alternatives=None,
                         accept=None,
                         spell_correct=False):
        cq = getattr(self, 'created_questions', 0)
        genre = self.db.Genre()
        genre.name = u"Genre %s" % (cq + 1)
        genre.approved = True
        genre.save()

        q = self.db.Question()
        q.text = text and unicode(text) or u'Question %s?' % (cq + 1)
        q.answer = unicode(answer)
        q.alternatives = (alternatives and alternatives
                          or [u'yes', u'no', u'maybe', u'perhaps'])
        q.genre = genre
        q.accept = accept and accept or []
        q.spell_correct = spell_correct
        q.state = u'PUBLISHED'
        q.publish_date = datetime.datetime.now()
        q.save()

        self.created_questions = cq + 1

        return q

    def _attach_image(self, question):
        question_image = self.db.QuestionImage()
        question_image.question = question
        question_image.render_attributes = {
          'src': '/static/image.jpg',
          'width': 300,
          'height': 260,
          'alt': question.text
        }
        question_image.save()

        here = os.path.dirname(__file__)
        image_data = open(os.path.join(here, 'image.jpg'), 'rb').read()
        with question_image.fs.new_file('original') as f:
            type_, __ = mimetypes.guess_type('image.jpg')
            f.content_type = type_
            f.write(image_data)

        assert question.has_image()
        return question_image

    def test_anonymous_to_existing_logged_in_after_play(self):
        peterbe = self.db.User()
        peterbe.username = u'peterbe'
        peterbe.save()

        play_points = self.db.PlayPoints()
        play_points.user = peterbe
        play_points.rules = self.default_rules_id
        play_points.points = 10
        play_points.wins = 1
        play_points.draws = 1
        play_points.losses = 1
        play_points.highscore_position = 2
        play_points.save()

        url = self.reverse_url('start_play')
        response = self.client.get(url)
        self.assertEqual(response.code, 302)
        user = self.db.User.one({'anonymous': True})
        self.assertTrue(user.anonymous)

        bob = self.db.User()
        bob.username = u'bob'
        bob.save()

        play = self.db.Play()
        play.users = [user, bob]
        play.rules = self.default_rules_id
        play.no_players = 2
        play.no_questions = 2
        play.started = datetime.datetime.now()
        play.save()

        q1 = self._create_question()
        q2 = self._create_question()

        # 1 point
        pq1a = self.db.PlayedQuestion()
        pq1a.play = play
        pq1a.question = q1
        pq1a.user = user
        pq1a.answer = u'yes'
        pq1a.alternatives = True
        pq1a.right = True
        pq1a.save()

        # 0 points
        pq1b = self.db.PlayedQuestion()
        pq1b.play = play
        pq1b.question = q1
        pq1b.user = bob
        pq1b.answer = u'wrong'
        pq1b.alternatives = True
        pq1b.right = False
        pq1b.save()

        # 0 points
        pq2a = self.db.PlayedQuestion()
        pq2a.play = play
        pq2a.question = q2
        pq2a.user = user
        pq2a.answer = u'wrong'
        pq2a.right = False
        pq2a.save()

        # 3 points
        pq2b = self.db.PlayedQuestion()
        pq2b.play = play
        pq2b.question = q2
        pq2b.user = bob
        pq2b.answer = u'yes'
        pq2b.right = True
        pq2b.save()

        play.winner = bob
        play.finished = datetime.datetime.now()
        play.save()

        from apps.play.models import PlayPoints

        play_points_user = PlayPoints.calculate(user, self.default_rules_id)
        self.assertEqual(play_points_user.draws, 0)
        self.assertEqual(play_points_user.wins, 0)
        self.assertEqual(play_points_user.losses, 1)
        self.assertEqual(play_points_user.points, 1)

        play_points_bob = PlayPoints.calculate(bob, self.default_rules_id)
        self.assertEqual(play_points_bob.draws, 0)
        self.assertEqual(play_points_bob.wins, 1)
        self.assertEqual(play_points_bob.losses, 0)
        self.assertEqual(play_points_bob.points, 3)

        # lastly, both people send each other a message
        msg1 = self.db.PlayMessage()
        msg1.play = play
        msg1['from'] = user
        msg1.to = bob
        msg1.message = u'Well done'
        msg1.save()

        msg2 = self.db.PlayMessage()
        msg2.play = play
        msg2['from'] = bob
        msg2.to = user
        msg2.message = u'Thanks'
        msg2.save()

        url = self.reverse_url('login')
        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        self.assertTrue('1 Kwissle point' in response.body)

        self.assertEqual(self.db.PlayPoints.find().count(), 3)

        from apps.main.handlers import TwitterAuthHandler
        TwitterAuthHandler.get_authenticated_user = \
          twitter_get_authenticated_user
        TwitterAuthHandler.authenticate_redirect = \
          twitter_authenticate_redirect
        url = self.reverse_url('auth_twitter')
        response = self.client.get(url)
        self.assertEqual(response.code, 302)
        self.assertTrue('twitter.com' in response.headers['location'])

        response = self.client.get(url, {'oauth_token':'xxx'})
        self.assertEqual(response.code, 302)

        peterbe = self.db.User.one({'username': 'peterbe'})
        self.assertTrue(peterbe)

        self.assertEqual(self.db.User.find().count(), 2)
        self.assertEqual(self.db.PlayedQuestion.find({'user.$id': peterbe._id}).count(), 2)
        self.assertEqual(self.db.PlayPoints.find({'user.$id': peterbe._id}).count(), 1)
        self.assertEqual(self.db.Play.find({'users.$id': peterbe._id}).count(), 1)
        self.assertEqual(self.db.PlayMessage.find({'from.$id': peterbe._id}).count(), 1)
        self.assertEqual(self.db.PlayMessage.find({'to.$id': peterbe._id}).count(), 1)

        play_points = self.db.PlayPoints.one({'user.$id': peterbe._id})
        self.assertEqual(play_points.points, 11)
        self.assertEqual(play_points.wins, 1)
        self.assertEqual(play_points.draws, 1)
        self.assertEqual(play_points.losses, 1 + 1)
        self.assertEqual(play_points.highscore_position, 1)

        self.assertEqual(self.db.PlayPoints.find().count(), 2)

    def test_render_some_help_pages(self):
        pages = ('About', 'a-good-question', 'rules', 'question-workflow',
                 'browsers')
        for p in pages:
            url = self.reverse_url('help', p)
            response = self.client.get(url)
            self.assertEqual(response.code, 200)

    def test_questions_page_anonymous_user(self):
        response = self.client.get(self.reverse_url('start_play'))
        self.assertEqual(response.code, 302)

        response = self.client.get('/')
        self.assertEqual(response.code, 200)

        url = self.reverse_url('questions')
        response = self.client.get(url)
        self.assertEqual(response.code, 302)
        self.assertEqual(settings.LOGIN_URL,
                         urlparse(response.headers['location']).path)

        self._login()
        response = self.client.get(url)
        self.assertEqual(response.code, 200)

    def test_sitemap_xml(self):
        # create a question
        q1 = self._create_question()
        q2 = self._create_question()
        image = self._attach_image(q2)
        url = self.reverse_url('sitemap_xml')
        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        self.assertEqual(response.headers['content-type'], 'application/xml')
        self.assertTrue(get_question_slug_url(q1) in response.body)
        self.assertTrue(image.render_attributes['src'] in response.body)
        url_regex = re.compile('<loc>(.*?)</loc>')
        for full_url in url_regex.findall(response.body):
            url = full_url.replace('http://', '')
            url = '/' + url.split('/', 1)[1]
            r = self.client.get(url)
            self.assertEqual(r.code, 200)

    def test_page_not_found(self):
        from apps.main.handlers import BaseHandler
        url = '/some/junk/'
        response = self.client.get(url)
        self.assertEqual(response.code, 404)
        self.assertTrue(BaseHandler.page_not_found_page_title
                        in response.body)

        url = '/some/junk'
        response = self.client.get(url)
        self.assertEqual(response.code, 302)
        self.assertEqual(response.headers['location'], '/some/junk/')

        url = '/some/junk?foo=bar'
        response = self.client.get(url)
        self.assertEqual(response.code, 302)
        self.assertEqual(response.headers['location'], '/some/junk/?foo=bar')

        url = '/questions'
        response = self.client.get(url)
        self.assertEqual(response.code, 302)
        self.assertEqual(response.headers['location'], '/questions/')

    def test_page_not_found_raised_in_handler(self):
        # if a handler raises an 404 it should show the 404.html template
        q = self._create_question(text="Peter's name?")
        url = get_question_slug_url(q)
        url = url.replace('Peter', 'Chris')

        from apps.main.handlers import BaseHandler
        response = self.client.get(url)
        self.assertEqual(response.code, 404)
        self.assertTrue(BaseHandler.page_not_found_page_title
                        in response.body)

    def test_sending_email_verification(self):
        self._login()
        user, = self.db.User.find()
        user.email = u''
        user.save()

        url = self.reverse_url('settings')
        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        data = {
          'email': 'new@email.com',
          'first_name': user.first_name,
          'last_name': user.last_name,
        }
        response = self.client.post(url, data)
        self.assertEqual(response.code, 302)
        email_sent = mail.outbox[-1]
        self.assertEqual(email_sent.to, ['new@email.com'])
        self.assertEqual(email_sent.from_email, settings.WEBMASTER)
        self.assertTrue('email verification' in email_sent.subject)
        regex = re.compile('(http.*?)\s')
        for url in regex.findall(email_sent.body):
            if 'verify-email' in urlparse(url).path:
                verify_url = urlparse(url).path

        # first mess with it a bit
        bogus_verify_url = self.reverse_url('verify_email',
                                            'xxxxxxxxxxxxx',
                                            'aaa')
        response = self.client.get(bogus_verify_url)
        self.assertEqual(response.code, 404)

        bogus_verify_url = self.reverse_url('verify_email',
                                            str(user._id).replace('0','1'),
                                            'aaa')
        response = self.client.get(bogus_verify_url)
        self.assertEqual(response.code, 404)

        bogus_verify_url = self.reverse_url('verify_email',
                                            user._id,
                                            'aaa')
        response = self.client.get(bogus_verify_url)
        self.assertEqual(response.code, 400)

        response = self.client.get(verify_url)
        self.assertEqual(response.code, 302)

        user_settings = self.db.UserSettings.one({'user': user._id})
        self.assertEqual(user_settings.email_verified, 'new@email.com')

    def test_browserid_login_stranger(self):
        url = self.reverse_url('auth_login_browserid')
        import apps.main.handlers
        _prev = apps.main.handlers.tornado.httpclient.AsyncHTTPClient
        try:
            apps.main.handlers.tornado.httpclient.AsyncHTTPClient = \
              make_mock_asynchttpclient({
                'status': 'okay',
                'email': 'peterbe@test.com',
              })

            response = self.client.post(url, {'assertion': 'xxx'})
            assert response.code == 200
            struct = json.loads(response.body)
            self.assertEqual(struct['next_url'], self.reverse_url('settings'))
        finally:
            apps.main.handlers.tornado.httpclient.AsyncHTTPClient = _prev

    def test_browserid_login_known(self):
        bob = self.db.User()
        bob.username = u'bob'
        bob.email = u'Peterbe@test.com'
        bob.save()

        url = self.reverse_url('auth_login_browserid')
        import apps.main.handlers
        _prev = apps.main.handlers.tornado.httpclient.AsyncHTTPClient
        try:
            apps.main.handlers.tornado.httpclient.AsyncHTTPClient = \
              make_mock_asynchttpclient({
                'status': 'okay',
                'email': 'peterbe@test.com',
              })

            response = self.client.post(url, {'assertion': 'xxx'})
            assert response.code == 200
            struct = json.loads(response.body)
            self.assertEqual(struct['next_url'], '/')
        finally:
            apps.main.handlers.tornado.httpclient.AsyncHTTPClient = _prev


    def test_browserid_login_clashing_username(self):
        bob = self.db.User()
        bob.username = u'bob'
        bob.email = u'bob@else.com'
        bob.save()

        bob2 = self.db.User()
        bob2.username = u'bob-2'
        bob2.email = u'bob@different.com'
        bob2.save()

        url = self.reverse_url('auth_login_browserid')
        import apps.main.handlers
        _prev = apps.main.handlers.tornado.httpclient.AsyncHTTPClient
        try:
            apps.main.handlers.tornado.httpclient.AsyncHTTPClient = \
              make_mock_asynchttpclient({
                'status': 'okay',
                'email': 'bob@test.com',
              })

            response = self.client.post(url, {'assertion': 'xxx'})
            assert response.code == 200
            struct = json.loads(response.body)
            self.assertEqual(struct['next_url'], self.reverse_url('settings'))
            self.assertTrue(self.db.User.one({'username': 'bob-3'}))
        finally:
            apps.main.handlers.tornado.httpclient.AsyncHTTPClient = _prev


class _Response(object):
    def __init__(self, code, body):
        self.code = code
        self.body = body

class MockAsyncHTTPClient(object):
    def __init__(self, response, status=200):
        self.status = status
        self.response = response

    def fetch(self, url, callback=None, *args, **kwargs):
        callback(_Response(self.status, self.response))

    def __call__(self):
        return self


def make_mock_asynchttpclient(response):
    return MockAsyncHTTPClient(json.dumps(response))


def google_get_authenticated_user(self, callback, **kw):
    callback({
      'locale': u'en-US',
      'first_name': u'Peter',
      'username': u'peterbe',
      'email': u'peterbe@gmail.com',
    })

def twitter_get_authenticated_user(self, callback, **kw):
    callback({
      'name': u'Peter Bengtsson',
      'username': u'peterbe',
      'email': None,
    })

def twitter_authenticate_redirect(self):
    self.redirect(self._OAUTH_AUTHENTICATE_URL)

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
