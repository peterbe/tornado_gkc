#__all__ = 'BaseModelsTestCase', 'BaseHTTPTestCase'

import base64
import time
import datetime
import mimetypes
import os
import re
import hmac
import hashlib
import unittest
import collections
from urllib import urlencode
from cStringIO import StringIO

from tornado.testing import LogTrapTestCase, AsyncHTTPTestCase

import app
import apps.main.models
from apps.main.models import connection
from tornado_utils.http_test_client import TestClient, HTTPClientMixin


class _DatabaseTestCaseMixin(object):
    _once = False

    def setup_connection(self):
        if not self._once:
            self._once = True
            self.db = connection['test']
            self._emptyCollections()

    def teardown_connection(self):
        # do this every time
        self._emptyCollections()

    def set_default_rules_id(self):
        default_rules = self.db.Rules()
        default_rules.name = u"Default rules"
        default_rules.default = True
        default_rules.save()
        self.default_rules_id = default_rules._id

    def _emptyCollections(self):
        [self.db.drop_collection(x) for x
         in self.db.collection_names()
         if x not in ('system.indexes',)]

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

    def _attach_knowledge(self, question):
        knowledge = {
          'right': .5,
          'wrong': .5,
          'alternatives_right': 0.,
          'alternatives_wrong': 0.,
          'too_slow': 0.,
          'timed_out': 0.,
          'users': 10,
        }
        self._create_question_knowledge(question, knowledge)

    def _create_question_knowledge(self, question, knowledge):
        sum_ = knowledge['right'] + \
               knowledge['wrong'] + \
               knowledge['alternatives_right'] + \
               knowledge['alternatives_wrong'] + \
               knowledge['too_slow'] + \
               knowledge['timed_out']
        assert round(sum_, 1) == 1.0, "%r <> 1" % round(sum_, 1)
        qk = self.db.QuestionKnowledge()
        qk.question = question
        qk.right = knowledge['right']
        qk.wrong = knowledge['wrong']
        qk.alternatives_right = knowledge['alternatives_right']
        qk.alternatives_wrong = knowledge['alternatives_wrong']
        qk.too_slow = knowledge['too_slow']
        qk.timed_out = knowledge['timed_out']
        qk.users = knowledge['users']
        qk.save()
        return qk

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

    def _create_play(self, users, rules=None, outcome=None):
        if rules is None:
            rules = self.db.Rules.one({'default': True})

        if outcome:
            no_questions = len(outcome)
        else:
            no_questions = rules.no_questions

        play = self.db.Play()
        play.rules = rules._id
        play.users = users
        play.no_questions = no_questions
        play.no_players = len(users)
        play.started = datetime.datetime.now() - datetime.timedelta(seconds=60)
        play.finished = datetime.datetime.now()
        play.save()

        if not outcome:
            # randomize the outcome
            outcome = []
            for i in range(no_questions):
                range_ = [3, 1, 1, 0, -1]
                row = []
                _prev = None
                for user in users:
                    random.shuffle(range_)
                    a = range_[0]
                    while a == _prev:
                        random.shuffle(range_)
                        a = range_[0]
                    row.append(a)
                    _prev = a
                outcome.append(row)

        counts = collections.defaultdict(int)
        for points in outcome:
            q = self._create_question()
            for i, user in enumerate(users):
                counts[user] += points[i]
                pq = self.db.PlayedQuestion()
                pq.play = play
                pq.question = q
                pq.user = user
                if points[i] > 0:
                    pq.right = True
                    pq.answer = u'Yes'
                    if points[i] > 1:
                        pq.alternatives = False
                    else:
                        pq.alternatives = True
                else:
                    pq.right = False
                    if points[i] < 0:
                        pq.answer = u'wrong'
                    pq.alternatives = False
                pq.save()

        highest_count = max(counts.values())
        for user in counts:
            if counts[user] == highest_count:
                if play.winner:
                    # one already set
                    play.winner = None
                    play.draw = True
                else:
                    play.winner = user

        play.save()
        return play


class BaseModelsTestCase(unittest.TestCase, _DatabaseTestCaseMixin):

    def setUp(self):
        super(BaseModelsTestCase, self).setUp()
        self.setup_connection()
        self.set_default_rules_id()

    def tearDown(self):
        super(BaseModelsTestCase, self).tearDown()
        self.teardown_connection()


class BaseAsyncTestCase(AsyncHTTPTestCase, _DatabaseTestCaseMixin):

    def setUp(self):
        super(BaseAsyncTestCase, self).setUp()
        self.setup_connection()
        self.set_default_rules_id()

    def tearDown(self):
        super(BaseAsyncTestCase, self).tearDown()
        self.teardown_connection()


class BaseHTTPTestCase(BaseAsyncTestCase, HTTPClientMixin):

    #_once = False
    def setUp(self):
        super(BaseHTTPTestCase, self).setUp()

        self._app.settings['email_backend'] = \
          'tornado_utils.send_mail.backends.locmem.EmailBackend'
        self._app.settings['email_exceptions'] = False
        self.client = TestClient(self)

    def get_app(self):
        return app.Application(database_name='test',
                               xsrf_cookies=False,
                               optimize_static_content=False,
                               embed_static_url=False)

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
        if client is None:
            client = self.client
        if not user:
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
        client.cookies['user'] = \
          self.create_signed_value('user', str(user._id))
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

    def _get_html_attributes(self, tag, html):
        _elem_regex = re.compile('<%s (.*?)>' % tag, re.M | re.DOTALL)
        _attrs_regex = re.compile('(\w+)="([^"]+)"')
        all_attrs = []
        for input in _elem_regex.findall(html):
            all_attrs.append(dict(_attrs_regex.findall(input)))
        return all_attrs
