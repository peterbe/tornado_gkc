import datetime
import time
import base64
import Cookie
import unittest
from apps.main.models import User
from apps.questions.models import Question, Genre
from playserver import Client, CookieParser

class BaseTestCase(unittest.TestCase):
    _once = False
    def setUp(self):
        if not self._once:
            self._once = True
            from mongokit import Connection
            self.con = Connection()
            self.con.register([User, Question, Genre])
            self.db = self.con.test
            self._emptyCollections()

    def _emptyCollections(self):
        [self.db.drop_collection(x) for x
         in self.db.collection_names()
         if x not in ('system.indexes',)]

    def tearDown(self):
        self._emptyCollections()
        del self.battles
        del self.current_client_battles

class MockClient(Client):
    def __init__(self, test):
        self.test = test
        self._sent = []
    def send(self, msg):
        self._sent.append(msg)

    @property
    def db(self):
        return self.test.db

    @property
    def battles(self):
        try:
            self.test.battles
        except AttributeError:
            self.test.battles = set()
        return self.test.battles

    @property
    def current_client_battles(self):
        try:
            self.test.current_client_battles
        except AttributeError:
            self.test.current_client_battles = {}
        return self.test.current_client_battles


class MockRequest:
    def __init__(self):
        self.headers = {}


class CookieMaker(CookieParser):
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


class ClientTestCase(BaseTestCase):

    def setUp(self):
        BaseTestCase.setUp(self)
        # create some questions

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


    def test_basic_client(self):
        client = MockClient(self)
        request = MockRequest()
        cookie = Cookie.BaseCookie()
        cookie_maker = CookieMaker(request)

        user = self.db.User()
        user.username = u'peterbe'
        user.save()

        cookie['user'] = cookie_maker.create_signed_value('user', str(user._id))
        request.headers['Cookie'] = cookie.output()
        client.on_open(request)
        self.assertTrue(client._sent)
        self.assertEqual(len(client._sent), 3)
        self.assertTrue(client._sent[0]['debug'])
        message = [x for x in client._sent if 'your_name' in x][0]
        self.assertEqual(message['your_name'], u'peterbe')

        # that should have created a new battle
        self.assertTrue(client.battles)
        self.assertEqual(len(client.battles), 1)
        # and it should have registered the user_id
        self.assertTrue(client.current_client_battles)
        self.assertTrue(client.current_client_battles[str(user._id)])
        battle = client.current_client_battles[str(user._id)]
        assert not battle.ready_to_play()
        assert battle.is_open()

        user2 = self.db.User()
        user2.username = u'chris'
        user2.save()

        client2 = MockClient(self)
        request = MockRequest()
        cookie = Cookie.BaseCookie()
        cookie_maker = CookieMaker(request)
        cookie['user'] = cookie_maker.create_signed_value('user', str(user2._id))
        request.headers['Cookie'] = cookie.output()
        client2.on_open(request)

        self.assertEqual(len(client.battles), 1)
        self.assertEqual(len(client2.battles), 1)
        assert client.battles == client2.battles
        self.assertEqual(len(client.current_client_battles), 2)
        assert battle.current_question is None

        # two clients have joined, the next question can be asked for in about
        # 3 seconds.
        last_message = client._sent[-1]
        assert last_message == client2._sent[-1]
        self.assertTrue(isinstance(last_message['wait'], int))
        self.assertTrue(last_message['wait'] > 0)
        # the added 0.1 is to adjust for the time it takes to get
        # here in the tests
        self.assertTrue((battle.min_wait_delay + 0.1) >=
                        (time.time() + last_message['wait']))

        # if you try to ask for next question too early you get an error
        client.on_message(dict(next_question=1))
        assert battle.current_question is None
        self.assertTrue(client._sent[-1]['error'])

        self._create_question()

        battle.min_wait_delay -= last_message['wait'] + 1
        client.on_message(dict(next_question=1))
        assert battle.current_question is not None

        last_message = client._sent[-1]
        self.assertEqual(last_message, client2._sent[-1])
        question = last_message['question']
        self.assertTrue(question['genre'])
        self.assertTrue(question['id'])
        self.assertTrue(question['text'])

        # nothing happens when when second client sends the 'next_question'
        _count_before = (len(client._sent), len(client2._sent))
        client2.on_message(dict(next_question='me too'))
        _count_after = (len(client._sent), len(client2._sent))
        self.assertEqual(_count_before, _count_after)

        # client2 sends an answer and gets it wrong
        client2.on_message(dict(answer='WRONG'))
        self.assertTrue(client._sent[-1]['has_answered'])
        self.assertTrue(client2._sent[-1]['answered'])
        self.assertTrue(not client2._sent[-1]['answered']['right'])

        # make sure there's a new question available
        self._create_question()
        client.on_message(dict(answer='Yes  '))


        self.assertTrue(client._sent[-3]['answered'])
        self.assertTrue(client._sent[-3]['answered']['right'])

        self.assertTrue(client2._sent[-3]['answered'])
        self.assertTrue(client2._sent[-3]['answered']['too_slow'])

        self.assertTrue(client._sent[-2]['update_scoreboard'])
        self.assertTrue(client2._sent[-2]['update_scoreboard'])

        self.assertTrue(client._sent[-1]['wait'])
        self.assertTrue(client2._sent[-1]['wait'])

        XXX let client2 get the next question right my loading alterantives
