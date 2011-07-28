import mimetypes
import os
from pymongo.objectid import ObjectId
import datetime
import time
import base64
import Cookie
import unittest
from pprint import pprint
from apps.main.models import User, connection
import apps.questions.models
import apps.play.models
from apps.play.cookies import CookieParser
from apps.play.client_app import Client
from apps.play import errors
import settings

class BaseTestCase(unittest.TestCase):
    _once = False
    def setUp(self):
        if not self._once:
            self._once = True
            self.db = connection.test
            self._emptyCollections()

    def _emptyCollections(self):
        [self.db.drop_collection(x) for x
         in self.db.collection_names()
         if x not in ('system.indexes',)]

    def tearDown(self):
        self._emptyCollections()
        try:
            del self.battles
            del self.current_client_battles
        except AttributeError:
            pass


class MockProtocol:
    pass


class MockClient(Client):
    def __init__(self, test):
        self.test = test
        self._sent = []
        self._protocol = MockProtocol()
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

class MockHeaderlessRequest:
    pass

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

    def _create_connected_client(self, username, request=None):
        client = MockClient(self)
        if not request:
            request = MockRequest()
        cookie = Cookie.BaseCookie()
        cookie_maker = CookieMaker(request)

        user = self.db.User()
        user.username = unicode(username)
        user.save()
        cookie['user'] = cookie_maker.create_signed_value('user', str(user._id))
        request.headers['Cookie'] = cookie.output()
        client.on_open(request)

        return user, client, request

    def _create_two_connected_clients(self):
        user, client, request = self._create_connected_client(
                                 u'peterbe')
        user2, client2, __ = self._create_connected_client(
                                 u'chris', request=request)
        return (user, client), (user2, client2)

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

    def test_client_repr(self):
        (user, client), (user2, client2) = self._create_two_connected_clients()
        r = repr(client)
        self.assertTrue(user.username in r)
        self.assertTrue(MockProtocol.__name__ in r)

    def test_connecting_without_headers_error(self):
        client = MockClient(self)
        request = MockHeaderlessRequest()
        cookie = Cookie.BaseCookie()
        cookie_maker = CookieMaker(request)

        client.on_open(request)
        self.assertTrue(client._sent[-1]['error'])
        self.assertEqual(client._sent[-1]['error']['code'],
                         errors.ERROR_NOT_LOGGED_IN)

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
        self.assertEqual(len(client._sent), 1)
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

        play = self.db.Play.one()
        assert play
        self.assertEqual(len(play.users), 2)
        self.assertEqual(len(play.users), play.no_players)

        self.assertTrue(play.no_questions)
        self.assertTrue(play.started)
        self.assertTrue(not play.halted)
        self.assertTrue(not play.finished)
        self.assertTrue(not play.draw)
        self.assertTrue(not play.winner)

        # two clients have joined, the next question can be asked for in about
        # 3 seconds.
        last_message = client._sent[-1]
        assert last_message == client2._sent[-1]
        self.assertTrue(isinstance(last_message['wait'], int))
        self.assertTrue(last_message['wait'] > 0)
        # the added 0.1 is to adjust for the time it takes to get
        # here in the tests
        a = battle.min_wait_delay + 0.2
        b = time.time() + last_message['wait']
        self.assertTrue(a >= b)


        # if you try to ask for next question too early you get an error
        client.on_message(dict(next_question=1))
        assert battle.current_question is None
        self.assertTrue(client._sent[-1]['error'])
        self.assertEqual(client._sent[-1]['error']['code'],
                         errors.ERROR_NEXT_QUESTION_TOO_SOON)

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

        self.assertEqual(
          self.db.PlayedQuestion.find({'play.$id': play._id}).count(),
          2)
        for played in self.db.PlayedQuestion.find():
            assert played.play._id == play._id
            self.assertEqual(str(played.question._id), question['id'])
            self.assertEqual(played.question.text, question['text'])
            self.assertEqual(played.question.genre.name, question['genre'])

        # nothing happens when when second client sends the 'next_question'
        _count_before = (len(client._sent), len(client2._sent))
        client2.on_message(dict(next_question='me too'))
        _count_after = (len(client._sent), len(client2._sent))
        self.assertEqual(_count_before, _count_after)

        self.assertEqual(
          self.db.PlayedQuestion.find({'play.$id': play._id}).count(),
          2)

        # client2 sends an answer and gets it wrong
        client2.on_message(dict(answer='WRONG'))
        played = self.db.PlayedQuestion.one({'user.$id': user2._id})
        self.assertEqual(played.answer, u'WRONG')
        self.assertTrue(not played.right)
        played = self.db.PlayedQuestion.one({'user.$id': user._id})
        self.assertEqual(played.answer, None)

        self.assertTrue(client._sent[-1]['has_answered'])
        self.assertTrue(client2._sent[-1]['answered'])
        self.assertTrue(not client2._sent[-1]['answered']['right'])

        # make sure there's a new question available
        question = self._create_question()
        client.on_message(dict(answer='Yes  '))

        self.assertTrue(client._sent[-3]['answered'])
        self.assertTrue(client._sent[-3]['answered']['right'])

        self.assertTrue(client2._sent[-3]['answered'])
        self.assertTrue(client2._sent[-3]['answered']['beaten'])

        self.assertTrue(client._sent[-2]['update_scoreboard'])
        self.assertTrue(client2._sent[-2]['update_scoreboard'])

        self.assertTrue(client._sent[-1]['wait'])
        self.assertTrue(client2._sent[-1]['wait'])

        played = self.db.PlayedQuestion.one({'user.$id': user._id})
        self.assertEqual(played.answer, u'Yes  ')
        self.assertTrue(played.right)

        self.assertEqual(
          self.db.PlayedQuestion.find({'play.$id': play._id}).count(), 2)

        battle.min_wait_delay -= 10 # anything
        client.on_message(dict(next_question=1))
        assert client._sent[-1] == client2._sent[-1]
        assert client._sent[-1]['question']['text'] == question.text

        self.assertEqual(
          self.db.PlayedQuestion.find({'play.$id': play._id}).count(), 4)

        client2.on_message(dict(alternatives=1))

        self.assertTrue(client2._sent[-1]['alternatives'])
        self.assertEqual(client2._sent[-1]['alternatives'],
                         question.alternatives)
        played = (self.db.PlayedQuestion
          .one({'user.$id': user2._id,
                'question.$id': battle.current_question._id}))
        self.assertTrue(played.alternatives)

        # suppose that client2 gets it right then
        alternative = [x for x in question.alternatives if x == question.answer][0]
        client2.on_message(dict(answer=alternative.upper()))
        self.assertEqual(client._sent[-2], client2._sent[-2])
        self.assertTrue(client._sent[-2]['update_scoreboard'])
        self.assertEqual(client._sent[-2]['update_scoreboard'][1], 1)

        self.assertTrue(client._sent[-1]['wait'])
        self.assertTrue(client2._sent[-1]['wait'])

        self._create_question(text=u"Is this no 2?")
        # let both people get it wrong this time
        battle.min_wait_delay -= 10 # anything
        client.on_message(dict(next_question=1))
        last_question_id = battle.current_question._id
        client.on_message(dict(answer='WRONG'))
        self.assertTrue(client2._sent[-1]['has_answered'])
        client2.on_message(dict(answer='ALSO WRONG'))

        self.assertTrue(not client2._sent[-3]['answered']['right'])
        self.assertTrue(client2._sent[-2]['answered']['both_wrong'])
        self.assertTrue(client._sent[-2]['answered']['both_wrong'])

        for played in (self.db.PlayedQuestion
                       .find({'question.$id': last_question_id})):
            self.assertTrue(not played.right)

        self.assertTrue(client._sent[-1]['wait'])
        self.assertTrue(client2._sent[-1]['wait'])

        self._create_question()
        battle.min_wait_delay -= 10 # anything
        client.on_message(dict(next_question=1))
        self.assertTrue(client._sent[-1]['question'])
        self.assertTrue(client2._sent[-1]['question'])

        # now pretend that both people are too slow
        client2.on_message(dict(timed_out=1))
        # you can't send this until there's been a delay
        self.assertTrue(client2._sent[-1]['error'])
        battle.current_question_sent -= battle.thinking_time # fake time
        # both will send this within nanoseconds of each other

        assert battle.current_question
        assert battle.current_question_sent

        _before = len(client._sent) + len(client2._sent)
        client.on_message(dict(timed_out=1))
        assert battle.current_question
        assert battle.current_question_sent
        _after = len(client._sent) + len(client2._sent)
        self.assertEqual(_before, _after)

        last_question_id = battle.current_question._id
        played = (self.db.PlayedQuestion
          .one({'user.$id': user._id,
                'question.$id': last_question_id}))
        self.assertTrue(played.timed_out)

        client2.on_message(dict(timed_out=1))
        _after_2 = len(client._sent) + len(client2._sent)
        self.assertNotEqual(_after, _after_2)

        played = (self.db.PlayedQuestion
          .one({'user.$id': user2._id,
                'question.$id': last_question_id}))
        self.assertTrue(played.timed_out)

        self.assertTrue(client._sent[-2]['answered']['too_slow'])
        self.assertTrue(client2._sent[-2]['answered']['too_slow'])

        self.assertTrue(client._sent[-1]['wait'])
        self.assertTrue(client2._sent[-1]['wait'])


    def test_both_too_slow_on_last_question(self):
        (user, client), (user2, client2) = self._create_two_connected_clients()
        battle = client.current_client_battles[str(user._id)]
        battle.no_questions = 2
        assert battle.current_question is None
        self._create_question()
        self._create_question()
        battle.min_wait_delay -= 3
        client.on_message(dict(next_question=1))
        self.assertTrue(client._sent[-1]['question'])
        self.assertTrue(client2._sent[-1]['question'])

        client.on_message(dict(answer='Yes'))
        self.assertEqual(client._sent[-2]['update_scoreboard'],
                         [u'peterbe', 3])
        self.assertTrue(client._sent[-2]['update_scoreboard'])
        self.assertTrue(client2._sent[-2]['update_scoreboard'])
        self.assertTrue(client._sent[-1]['wait'])
        self.assertTrue(client2._sent[-1]['wait'])

        battle.min_wait_delay -= 3
        client.on_message(dict(next_question=1))
        self.assertTrue(client._sent[-1]['question'])
        self.assertTrue(client2._sent[-1]['question'])

        # now pretend that both people are too slow
        battle.current_question_sent -= battle.thinking_time # fake time
        last_question_id = battle.current_question._id
        client.on_message(dict(timed_out=1))
        from time import sleep
        sleep(0.1)
        client2.on_message(dict(timed_out=1))

        self.assertTrue(client._sent[-3]['answered']['too_slow'])
        self.assertTrue(client2._sent[-3]['answered']['too_slow'])

        self.assertTrue(client._sent[-2]['play_id'])
        self.assertTrue(client2._sent[-2]['play_id'])
        self.assertEqual(client._sent[-2]['play_id'],
                         client2._sent[-2]['play_id'])
        play_id = client2._sent[-2]['play_id']
        play = self.db.Play.one({'_id': ObjectId(play_id)})
        self.assertEqual(play.winner.username, client.user_name)

        self.assertTrue(client._sent[-1]['winner']['you_won'])
        self.assertTrue(not client2._sent[-1]['winner']['you_won'])
        assert self.db.PlayedQuestion.one({
          'timed_out': True,
          'user.$id': user._id,
          'question.$id': last_question_id,
        })
        assert self.db.PlayedQuestion.one({
          'timed_out': True,
          'user.$id': user2._id,
          'question.$id': last_question_id,
        })

        play = self.db.Play.one()
        self.assertTrue(not play.draw)
        self.assertTrue(play.finished)
        self.assertEqual(play.winner._id, user._id)

    def test_timed_out_after_correct_answer(self):
        """if one client sends the correct answer, that will close the current
        question and send both of them a wait delay.
        If the second client ignores that and sends a timed_out that should
        then be ignored in favor of the new question"""
        (user, client), (user2, client2) = self._create_two_connected_clients()
        battle = client.current_client_battles[str(user._id)]
        battle.no_questions = 2
        self._create_question()
        self._create_question()

        battle.min_wait_delay -= 3
        client.on_message(dict(next_question=1))
        self.assertTrue(client._sent[-1]['question'])
        self.assertTrue(client2._sent[-1]['question'])

        client.on_message(dict(answer='Yes'))
        client2.on_message(dict(timed_out=1))

        self.assertTrue(client._sent[-2]['update_scoreboard'])
        self.assertTrue(client2._sent[-2]['update_scoreboard'])

        self.assertTrue(client._sent[-1]['wait'])
        self.assertTrue(client2._sent[-1]['wait'])

    def test_timed_out_after_wrong_answer(self):
        """if one client sends the correct answer, that will close the current
        question and send both of them a wait delay.
        If the second client ignores that and sends a timed_out that should
        then be ignored in favor of the new question"""
        (user, client), (user2, client2) = self._create_two_connected_clients()
        battle = client.current_client_battles[str(user._id)]
        battle.no_questions = 3
        self._create_question()
        self._create_question()
        self._create_question()

        battle.min_wait_delay -= 3
        client.on_message(dict(next_question=1))
        self.assertTrue(client._sent[-1]['question'])
        self.assertTrue(client2._sent[-1]['question'])

        client.on_message(dict(answer='WRONG'))
        battle.current_question_sent -= battle.thinking_time # fake time
        client2.on_message(dict(timed_out=1))
        self.assertTrue(client._sent[-1]['wait'])
        self.assertTrue(client2._sent[-1]['wait'])

    def test_first_wrong_second_right(self):
        (user, client), (user2, client2) = self._create_two_connected_clients()
        battle = client.current_client_battles[str(user._id)]
        battle.no_questions = 3
        self._create_question()
        self._create_question()
        self._create_question()

        battle.min_wait_delay -= 3
        client.on_message(dict(next_question=1))
        self.assertTrue(client._sent[-1]['question'])
        self.assertTrue(client2._sent[-1]['question'])

        client.on_message(dict(answer='WRONG'))
        self.assertTrue(client._sent[-1]['answered'])
        self.assertTrue(not client._sent[-1]['answered']['right'])
        self.assertTrue(client2._sent[-1]['has_answered'])

        client2.on_message(dict(answer='Yes'))

        self.assertTrue(client._sent[-3]['answered']['beaten'])
        self.assertTrue(client2._sent[-3]['answered']['right'])

        self.assertTrue(client._sent[-2]['update_scoreboard'])
        self.assertTrue(client2._sent[-2]['update_scoreboard'])
        self.assertTrue(client._sent[-1]['wait'])
        self.assertTrue(client2._sent[-1]['wait'])

    def test_joining_same_user_different_clients(self):
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

        client2 = MockClient(self)
        request = MockRequest()
        cookie = Cookie.BaseCookie()
        cookie_maker = CookieMaker(request)
        cookie['user'] = cookie_maker.create_signed_value('user', str(user._id))
        request.headers['Cookie'] = cookie.output()
        client2.on_open(request)

        self.assertTrue(client2._sent[-1]['error'])

    def test_loading_alternatives_too_late(self):
        (user, client), (user2, client2) = self._create_two_connected_clients()
        battle = client.current_client_battles[str(user._id)]
        battle.no_questions = 3
        self._create_question()
        self._create_question()
        self._create_question()

        battle.min_wait_delay -= 3
        client.on_message(dict(next_question=1))
        self.assertTrue(client._sent[-1]['question'])
        self.assertTrue(client2._sent[-1]['question'])
        client.on_message(dict(answer='yes'))
        client2.on_message(dict(alternatives=1))

        self.assertTrue(client._sent[-3]['answered']['right'])
        self.assertTrue(client2._sent[-3]['answered']['too_slow'])

        self.assertTrue(client._sent[-1]['wait'])
        self.assertTrue(client2._sent[-1]['wait'])

    def test_no_questions__author(self):
        # 3 questions, 1 written by client1 and 1 written by client2
        (user, client), (user2, client2) = self._create_two_connected_clients()
        battle = client.current_client_battles[str(user._id)]
        battle.no_questions = 3
        q1 = self._create_question()
        q2 = self._create_question()
        q3 = self._create_question()

        q1.author = user
        q1.save()
        q2.author = user2
        q2.save()

        battle.min_wait_delay -= 3
        client.on_message(dict(next_question=1))
        self.assertTrue(client._sent[-1]['question'])
        self.assertTrue(client2._sent[-1]['question'])
        self.assertEqual(client._sent[-1]['question']['text'], q3.text)
        client.on_message(dict(answer='yes'))
        self.assertTrue(client._sent[-1]['wait'])
        self.assertTrue(client2._sent[-1]['wait'])
        battle.min_wait_delay -= 3
        client.on_message(dict(next_question=1))

        self.assertTrue(client._sent[-1]['error'])
        self.assertTrue(client2._sent[-1]['error'])

        self.assertEqual(client._sent[-1]['error']['code'],
                         errors.ERROR_NO_MORE_QUESTIONS)

    def test_battle_draw(self):
        (user, client), (user2, client2) = self._create_two_connected_clients()
        battle = client.current_client_battles[str(user._id)]
        battle.no_questions = 4
        self._create_question()
        self._create_question()
        self._create_question()
        self._create_question()

        battle.min_wait_delay -= 3
        client.on_message(dict(next_question=1))
        client.on_message(dict(alternatives=1))
        client.on_message(dict(answer='yes'))
        self.assertTrue(client._sent[-1]['wait'])
        self.assertTrue(client2._sent[-1]['wait'])
        battle.min_wait_delay -= 3
        client.on_message(dict(next_question=1))
        client.on_message(dict(alternatives=1))
        client.on_message(dict(answer='YES'))
        self.assertTrue(client._sent[-1]['wait'])
        self.assertTrue(client2._sent[-1]['wait'])
        battle.min_wait_delay -= 3
        client.on_message(dict(next_question=1))
        client.on_message(dict(alternatives=1))
        client.on_message(dict(answer='YEs '))
        self.assertTrue(client._sent[-1]['wait'])
        self.assertTrue(client2._sent[-1]['wait'])
        battle.min_wait_delay -= 3
        client.on_message(dict(next_question=1))
        client2.on_message(dict(answer='YES'))

        self.assertTrue(client._sent[-1]['winner']['draw'])
        self.assertTrue(client2._sent[-1]['winner']['draw'])

        play = self.db.Play.one()
        self.assertEqual(play.winner, None)
        self.assertTrue(play.draw)


    def test_disconnect_twice(self):
        (user, client), (user2, client2) = self._create_two_connected_clients()
        battle = client.current_client_battles[str(user._id)]
        battle.no_questions = 3
        q1 = self._create_question()
        q2 = self._create_question()
        q3 = self._create_question()

        battle.min_wait_delay -= 3
        client.on_message(dict(next_question=1))
        self.assertTrue(client._sent[-1]['question'])
        self.assertTrue(client2._sent[-1]['question'])
        client.on_message(dict(answer='yes'))
        self.assertTrue(client._sent[-1]['wait'])
        self.assertTrue(client2._sent[-1]['wait'])

        client.on_close()
        self.assertTrue(client2._sent[-1]['disconnected'])
        self.assertEqual(client2._sent[-1]['disconnected'],
                         user.username)
        client2_msgs = client2._sent[:]
        client.on_close()
        self.assertEqual(len(client2_msgs),
                         len(client2._sent))

    def test_getting_alternatives_too_late(self):
        (user, client), (user2, client2) = self._create_two_connected_clients()
        battle = client.current_client_battles[str(user._id)]
        battle.no_questions = 1
        q1 = self._create_question()

        battle.min_wait_delay -= 3
        client.on_message(dict(next_question=1))
        self.assertTrue(client._sent[-1]['question'])
        self.assertTrue(client2._sent[-1]['question'])
        client.on_message(dict(answer='Yes'))
        client2.on_message(dict(alternatives=1))

        self.assertTrue(client._sent[-1]['winner'])
        self.assertTrue(client2._sent[-1]['winner'])

        self.assertTrue(client._sent[-1]['winner']['you_won'])
        self.assertTrue(not client2._sent[-1]['winner']['you_won'])

    def test_sending_right_answer_too_late(self):
        (user, client), (user2, client2) = self._create_two_connected_clients()
        battle = client.current_client_battles[str(user._id)]
        battle.no_questions = 1
        q1 = self._create_question()

        battle.min_wait_delay -= 3
        client.on_message(dict(next_question=1))
        self.assertTrue(client._sent[-1]['question'])
        self.assertTrue(client2._sent[-1]['question'])
        client.on_message(dict(answer='Yes'))
        client2.on_message(dict(answer='yes'))

        self.assertTrue(client._sent[-1]['winner'])
        self.assertTrue(client2._sent[-1]['winner'])

        self.assertTrue(client._sent[-1]['winner']['you_won'])
        self.assertTrue(not client2._sent[-1]['winner']['you_won'])

    def test_sending_wrong_answer_too_late(self):
        (user, client), (user2, client2) = self._create_two_connected_clients()
        battle = client.current_client_battles[str(user._id)]
        battle.no_questions = 1
        q1 = self._create_question()

        battle.min_wait_delay -= 3
        client.on_message(dict(next_question=1))
        self.assertTrue(client._sent[-1]['question'])
        self.assertTrue(client2._sent[-1]['question'])
        client.on_message(dict(answer='Yes'))
        client2.on_message(dict(answer='WRong'))

        self.assertTrue(client._sent[-1]['winner'])
        self.assertTrue(client2._sent[-1]['winner'])

        self.assertTrue(client._sent[-1]['winner']['you_won'])
        self.assertTrue(not client2._sent[-1]['winner']['you_won'])

    def test_sending_timed_out_too_late(self):
        (user, client), (user2, client2) = self._create_two_connected_clients()
        battle = client.current_client_battles[str(user._id)]
        battle.no_questions = 1
        q1 = self._create_question()

        battle.min_wait_delay -= 3
        client.on_message(dict(next_question=1))

        self.assertTrue(client._sent[-1]['question'])
        self.assertTrue(client2._sent[-1]['question'])
        client.on_message(dict(answer='Yes'))
        client2.on_message(dict(timed_out=1))

        self.assertTrue(client._sent[-1]['winner'])
        self.assertTrue(client2._sent[-1]['winner'])

        self.assertTrue(client._sent[-1]['winner']['you_won'])
        self.assertTrue(not client2._sent[-1]['winner']['you_won'])

    def test_bot_sending_answer_too_late(self):
        user, client, request = self._create_connected_client('peterbe')
        battle = client.current_client_battles[str(user._id)]
        battle.no_questions = 1
        client.on_message(dict(against_computer=1))

        q1 = self._create_question()
        qk1 = self._create_question_knowledge(q1, {
          'right': 1.0,
          'wrong': 0.,
          'alternatives_right': 0.,
          'alternatives_wrong': 0.,
          'too_slow': 0.,
          'timed_out': 0.,
          'users': 10,
        })

        battle.min_wait_delay -= client._sent[-1]['wait']
        client.on_message(dict(next_question=1))

        self.assertTrue(client._sent[-1]['bot_answers'])
        bot_answers_seconds = client._sent[-1]['bot_answers']

        self.assertTrue(client._sent[-2]['question'])
        battle.min_wait_delay -= bot_answers_seconds
        client.on_message(dict(answer='Yes'))
        client.on_message(dict(bot_answers='Yes'))

        self.assertTrue(client._sent[-1]['winner'])
        self.assertTrue(client._sent[-1]['winner']['you_won'])

    def test_playing_against_computer(self):
        user, client, request = self._create_connected_client('peterbe')
        client.on_message(dict(against_computer=1))
        self.assertTrue(client._sent[-1]['wait'])
        self.assertTrue(client._sent[-2]['init_scoreboard'])
        user_names = client._sent[-2]['init_scoreboard']

        q1 = self._create_question()
        q2 = self._create_question()
        q3 = self._create_question()

        qk1 = self._create_question_knowledge(q1, {
          'right': 0.3,
          'wrong': 0.1,
          'alternatives_right': 0.1,
          'alternatives_wrong': 0.1,
          'too_slow': 0.3,
          'timed_out': 0.1,
          'users': 10,
        })
        qk2 = self._create_question_knowledge(q3, {
          'right': 0.3,
          'wrong': 0.1,
          'alternatives_right': 0.1,
          'alternatives_wrong': 0.1,
          'too_slow': 0.3,
          'timed_out': 0.1,
          'users': 10,
        })

        self.assertTrue(u'peterbe' in user_names)
        self.assertTrue(settings.COMPUTER_USERNAME in user_names)
        # pretend that we have waited X seconds
        battle = client.current_client_battles[str(user._id)]
        battle.min_wait_delay -= client._sent[-1]['wait']
        client.on_message(dict(next_question=1))
        self.assertTrue(client._sent[-1]['bot_answers'])
        bot_answers_seconds = client._sent[-1]['bot_answers']
        self.assertTrue(bot_answers_seconds > 0)
        self.assertTrue(bot_answers_seconds <= battle.thinking_time)
        # pretend the user does nothing
        battle.min_wait_delay -= bot_answers_seconds
        client.on_message(dict(bot_answers=1))
        # since the outcome is already decided we know what to expect
        self.assertTrue(battle.bot_answer)
        self.assertEqual(bot_answers_seconds, battle.bot_answer['seconds'])
        self.assertTrue(battle.bot_answer['alternatives'] in (True, False))
        self.assertTrue(battle.bot_answer['right'] in (True, False))
        self.assertTrue(battle.bot_answer['wrong'] in (True, False))

        if battle.bot_answer['right']:
            if battle.bot_answer['alternatives']:
                self.assertTrue(client._sent[-3]['answered'])
                self.assertTrue(client._sent[-3]['answered']['too_slow'])
                self.assertTrue(client._sent[-2]['update_scoreboard'])
                self.assertEqual(client._sent[-2]['update_scoreboard'],
                                 [settings.COMPUTER_USERNAME, 1])
                self.assertTrue(client._sent[-1]['wait'])
            else:
                self.assertTrue(client._sent[-3]['answered'])
                self.assertTrue(client._sent[-3]['answered']['too_slow'])
                self.assertTrue(client._sent[-2]['update_scoreboard'])
                self.assertEqual(client._sent[-2]['update_scoreboard'],
                                 [settings.COMPUTER_USERNAME, 3])
                self.assertTrue(client._sent[-1]['wait'])
        elif battle.bot_answer['wrong']:
            if battle.bot_answer['alternatives']:
                self.assertTrue(client._sent[-1]['has_answered'])
                self.assertEqual(client._sent[-1]['has_answered'],
                                settings.COMPUTER_USERNAME)
            else:
                self.assertTrue(client._sent[-1]['has_answered'])
                self.assertEqual(client._sent[-1]['has_answered'],
                                settings.COMPUTER_USERNAME)

    def test_beat_computer(self):
        user, client, request = self._create_connected_client('peterbe')
        client.on_message(dict(against_computer=1))
        user_names = client._sent[-2]['init_scoreboard']

        q1 = self._create_question()
        q2 = self._create_question()

        qk1 = self._create_question_knowledge(q1, {
          'right': 0.3,
          'wrong': 0.1,
          'alternatives_right': 0.1,
          'alternatives_wrong': 0.1,
          'too_slow': 0.3,
          'timed_out': 0.1,
          'users': 10,
        })
        qk2 = self._create_question_knowledge(q2, {
          'right': 0.3,
          'wrong': 0.1,
          'alternatives_right': 0.1,
          'alternatives_wrong': 0.1,
          'too_slow': 0.3,
          'timed_out': 0.1,
          'users': 10,
        })

        self.assertTrue(u'peterbe' in user_names)
        self.assertTrue(settings.COMPUTER_USERNAME in user_names)

        battle = client.current_client_battles[str(user._id)]
        battle.no_questions = 2

        battle.min_wait_delay -= client._sent[-1]['wait']
        client.on_message(dict(next_question=1))
        self.assertTrue(client._sent[-1]['bot_answers'])
        bot_answers_seconds = client._sent[-1]['bot_answers']

        battle.min_wait_delay -= bot_answers_seconds
        client.on_message(dict(alternatives=1))
        self.assertTrue(client._sent[-1]['alternatives'])
        client.on_message(dict(answer='YES'))

        self.assertTrue(client._sent[-3]['answered'])
        self.assertTrue(client._sent[-3]['answered']['right'])
        self.assertTrue(client._sent[-2]['update_scoreboard'])
        self.assertEqual(client._sent[-2]['update_scoreboard'],
                         [u'peterbe', 1])
        self.assertTrue(client._sent[-1]['wait'])

        battle.min_wait_delay -= bot_answers_seconds
        client.on_message(dict(next_question=1))

        self.assertTrue(client._sent[-2]['question'])
        self.assertTrue(client._sent[-1]['bot_answers'])
        client.on_message(dict(answer='Yes'))

        self.assertTrue(client._sent[-3]['update_scoreboard'])
        self.assertEqual(client._sent[-3]['update_scoreboard'],
                         [u'peterbe', 3])

        self.assertTrue(client._sent[-2]['play_id'])
        self.assertTrue(client._sent[-1]['winner'])
        self.assertTrue(client._sent[-1]['winner']['you_won'])
        play_id = client._sent[-2]['play_id']

        play = self.db.Play.one({'_id': ObjectId(play_id)})
        self.assertEqual(len(play.users), 2)
        self.assertTrue(settings.COMPUTER_USERNAME in
                        [x.username for x in play.users])
        self.assertTrue(play.finished)
        self.assertFalse(play.draw)
        self.assertEqual(play.winner.username, u'peterbe')

    def test_draw_against_computer(self):
        user, client, request = self._create_connected_client('peterbe')
        client.on_message(dict(against_computer=1))
        user_names = client._sent[-2]['init_scoreboard']

        q1 = self._create_question()
        q2 = self._create_question()

        qk1 = self._create_question_knowledge(q1, {
          'right': 1.,
          'wrong': 0.,
          'alternatives_right': 0.,
          'alternatives_wrong': 0.,
          'too_slow': 0.,
          'timed_out': 0.,
          'users': 10,
        })
        qk2 = self._create_question_knowledge(q2, {
          'right': 1.,
          'wrong': 0.,
          'alternatives_right': 0.,
          'alternatives_wrong': 0.,
          'too_slow': 0.,
          'timed_out': 0.,
          'users': 10,
        })

        self.assertTrue(u'peterbe' in user_names)
        self.assertTrue(settings.COMPUTER_USERNAME in user_names)

        battle = client.current_client_battles[str(user._id)]
        battle.no_questions = 2

        battle.min_wait_delay -= client._sent[-1]['wait']
        client.on_message(dict(next_question=1))
        self.assertTrue(client._sent[-1]['bot_answers'])
        bot_answers_seconds = client._sent[-1]['bot_answers']

        battle.min_wait_delay -= bot_answers_seconds
        client.on_message(dict(answer='YES'))
        self.assertTrue(client._sent[-3]['answered'])
        self.assertTrue(client._sent[-3]['answered']['right'])
        self.assertTrue(client._sent[-2]['update_scoreboard'])
        self.assertEqual(client._sent[-2]['update_scoreboard'],
                         [u'peterbe', 3])
        self.assertTrue(client._sent[-1]['wait'])
        battle.min_wait_delay -= client._sent[-1]['wait']
        client.on_message(dict(next_question=1))


        battle.min_wait_delay -= bot_answers_seconds
        client.on_message(dict(bot_answers=1))
        if battle.bot_answer['right']:
            if not battle.bot_answer['alternatives']:
                self.assertTrue(client._sent[-4]['answered'])
                self.assertTrue(client._sent[-4]['answered']['too_slow'])
                self.assertTrue(client._sent[-3]['update_scoreboard'])
                self.assertEqual(client._sent[-3]['update_scoreboard'],
                                 [settings.COMPUTER_USERNAME, 3])

                self.assertTrue(client._sent[-1]['winner'])
                self.assertTrue(client._sent[-1]['winner']['draw'])

                self.assertTrue(client._sent[-2]['play_id'])
                play_id = client._sent[-2]['play_id']

                play = self.db.Play.one({'_id': ObjectId(play_id)})
                self.assertEqual(len(play.users), 2)
                self.assertTrue(settings.COMPUTER_USERNAME in
                                [x.username for x in play.users])
                self.assertTrue(play.finished)
                self.assertTrue(play.draw)
                self.assertTrue(not play.winner)

    def test_play_questions_with_image(self):
        (user, client), (user2, client2) = self._create_two_connected_clients()
        battle = client.current_client_battles[str(user._id)]
        battle.no_questions = 2
        q1 = self._create_question()
        self._attach_image(q1)
        q2 = self._create_question()
        self._attach_image(q2)

        battle.min_wait_delay -= 3
        client.on_message(dict(next_question=1))
        self.assertTrue(client._sent[-1]['question'])
        self.assertTrue(client2._sent[-1]['question'])
        self.assertTrue(client._sent[-1]['question']['image'])
        self.assertTrue(client2._sent[-1]['question']['image'])
        image = client._sent[-1]['question']['image']
        self.assertTrue(image['src'])
        self.assertTrue(image['width'])
        self.assertTrue(image['height'])
        self.assertTrue(image['alt'])

        client.on_message(dict(loaded_image=1))
        # meaning it took client2 1 second load the image
        battle.min_wait_delay -= 1
        client2.on_message(dict(loaded_image=1))

        self.assertTrue(client._sent[-1]['show_image'])
        self.assertTrue(client2._sent[-1]['show_image'])

        client.on_message(dict(answer='Yes'))

        self.assertTrue(client._sent[-3]['answered']['right'])
        self.assertTrue(client2._sent[-3]['answered']['too_slow'])
        self.assertEqual(client._sent[-2]['update_scoreboard'],
                        [u'peterbe', 3])
        self.assertEqual(client2._sent[-2]['update_scoreboard'],
                        [u'peterbe', 3])
        self.assertTrue(client._sent[-1]['wait'])
        self.assertTrue(client2._sent[-1]['wait'])


    def test_answer_before_loaded_image(self):
        (user, client), (user2, client2) = self._create_two_connected_clients()
        battle = client.current_client_battles[str(user._id)]
        battle.no_questions = 1
        q1 = self._create_question()
        self._attach_image(q1)

        battle.min_wait_delay -= 3
        client.on_message(dict(next_question=1))
        self.assertTrue(client._sent[-1]['question'])
        self.assertTrue(client2._sent[-1]['question'])
        self.assertTrue(client._sent[-1]['question']['image'])
        self.assertTrue(client2._sent[-1]['question']['image'])


        # if you try to send an answer before both clients have
        # acknowledged loading the image you get an error
        client.on_message(dict(answer='Yes'))
        self.assertEqual(client._sent[-1]['error']['code'],
                         errors.ERROR_ANSWER_BEFORE_IMAGE_LOADED)


    def test_answer_before_loaded_image_second_question(self):
        (user, client), (user2, client2) = self._create_two_connected_clients()
        battle = client.current_client_battles[str(user._id)]
        battle.no_questions = 2
        q1 = self._create_question()
        self._attach_image(q1)
        q2 = self._create_question()
        self._attach_image(q2)

        battle.min_wait_delay -= 3
        client.on_message(dict(next_question=1))
        self.assertTrue(client._sent[-1]['question'])
        self.assertTrue(client2._sent[-1]['question'])
        self.assertTrue(client._sent[-1]['question']['image'])
        self.assertTrue(client2._sent[-1]['question']['image'])

        client.on_message(dict(loaded_image=1))
        # meaning it took client2 1 second load the image
        battle.min_wait_delay -= 1
        client2.on_message(dict(loaded_image=1))

        self.assertTrue(client._sent[-1]['show_image'])
        self.assertTrue(client2._sent[-1]['show_image'])

        client.on_message(dict(answer='Yes'))

        self.assertTrue(client._sent[-3]['answered']['right'])
        self.assertTrue(client2._sent[-3]['answered']['too_slow'])
        self.assertEqual(client._sent[-2]['update_scoreboard'],
                        [u'peterbe', 3])
        self.assertEqual(client2._sent[-2]['update_scoreboard'],
                        [u'peterbe', 3])
        self.assertTrue(client._sent[-1]['wait'])
        self.assertTrue(client2._sent[-1]['wait'])

        battle.min_wait_delay -= 3
        client.on_message(dict(next_question=1))
        client2.on_message(dict(next_question=1))

        self.assertTrue(client._sent[-1]['question'])
        self.assertTrue(client2._sent[-1]['question'])
        self.assertTrue(client._sent[-1]['question']['image'])
        self.assertTrue(client2._sent[-1]['question']['image'])

        client.on_message(dict(loaded_image=1))
        # if you try to send an answer before both clients have
        # acknowledged loading the image you get an error
        client.on_message(dict(answer='Yes'))
        client2.on_message(dict(loaded_image=1))

        self.assertEqual(client._sent[-1]['error']['code'],
                         errors.ERROR_ANSWER_BEFORE_IMAGE_LOADED)

    def test_next_question_timing(self):
        (user, client), (user2, client2) = self._create_two_connected_clients()
        battle = client.current_client_battles[str(user._id)]
        battle.no_questions = 2
        q1 = self._create_question()
        q2 = self._create_question()

        battle.min_wait_delay -= 3
        client.on_message(dict(next_question=1))
        self.assertTrue(client._sent[-1]['question'])
        self.assertTrue(client2._sent[-1]['question'])
        client.on_message(dict(alternatives=1))
        client.on_message(dict(answer='Yes'))

        self.assertTrue(client._sent[-3]['answered']['right'])
        self.assertTrue(client2._sent[-3]['answered']['too_slow'])

        self.assertTrue(client._sent[-2]['update_scoreboard'])
        self.assertTrue(client2._sent[-2]['update_scoreboard'])

    def test_run_out_recently_played(self):
        (user, client), (user2, client2) = self._create_two_connected_clients()
        battle = client.current_client_battles[str(user._id)]
        battle.no_questions = 3
        print self.db.Play.find().count()
        q1 = self._create_question()
        q2 = self._create_question()
        p = self.db.Play()
        p.users = [user, user2]
        p.no_players = 2
        p.no_questions = 2
        p.finished = datetime.datetime.now() - datetime.timedelta(seconds=60 * 60 - 1)
        p.draw = True
        p.save()

        pq1a = self.db.PlayedQuestion()
        pq1a.play = p
        pq1a.question = q1
        pq1a.user = user
        pq1a.right = True
        pq1a.answer = u'yes'
        pq1a.time = 1.0
        pq1a.save()

        pq1b = self.db.PlayedQuestion()
        pq1b.play = p
        pq1b.question = q1
        pq1b.user = user2
        pq1b.right = False
        pq1b.answer = u'wrong'
        pq1b.time = 1.0
        pq1b.save()

        pq2a = self.db.PlayedQuestion()
        pq2a.play = p
        pq2a.question = q2
        pq2a.user = user
        pq2a.right = False
        pq2a.answer = u'wrong'
        pq2a.time = 2.0
        pq2a.save()

        pq2b = self.db.PlayedQuestion()
        pq2b.play = p
        pq2b.question = q2
        pq2b.user = user2
        pq2b.right = True
        pq2b.answer = u'yes'
        pq2b.time = 2.0
        pq2b.save()

        q3 = self._create_question()
        q4 = self._create_question()

        battle.min_wait_delay -= 3
        client.on_message(dict(next_question=1))
        self.assertTrue(client._sent[-1]['question'])
        self.assertTrue(client2._sent[-1]['question'])
        client.on_message(dict(alternatives=1))
        client.on_message(dict(answer='Yes'))

        self.assertTrue(client._sent[-3]['answered']['right'])
        self.assertTrue(client2._sent[-3]['answered']['too_slow'])

        self.assertTrue(client._sent[-1]['wait'])
        self.assertTrue(client2._sent[-1]['wait'])

        battle.min_wait_delay -= 3
        client.on_message(dict(next_question=1))

        client.on_message(dict(next_question=1))
        client2.on_message(dict(next_question=1))

        self.assertTrue(client._sent[-1]['question'])
        self.assertTrue(client2._sent[-1]['question'])

        client2.on_message(dict(alternatives=1))
        client2.on_message(dict(answer='Yes'))

        self.assertTrue(client._sent[-3]['answered']['too_slow'])
        self.assertTrue(client2._sent[-3]['answered']['right'])

        self.assertTrue(client._sent[-1]['wait'])
        self.assertTrue(client2._sent[-1]['wait'])

        battle.min_wait_delay -= 3
        client.on_message(dict(next_question=1))

        self.assertTrue(client._sent[-1]['error'])
        self.assertTrue(client2._sent[-1]['error'])

        self.assertEqual(client._sent[-1]['error']['code'],
                         errors.ERROR_NO_MORE_QUESTIONS)
        self.assertEqual(client2._sent[-1]['error']['code'],
                         errors.ERROR_NO_MORE_QUESTIONS)

    def test_dont_run_out_recently_played_against_computer(self):
        user2 = self.db.User()
        user2.username = u'peppe'
        user2.save()

        computer = self.db.User()
        computer.username = settings.COMPUTER_USERNAME
        computer.save()

        q1 = self._create_question()
        self._create_question_knowledge(q1, {
          'right': .8,
          'wrong': .2,
          'alternatives_right': 0.,
          'alternatives_wrong': 0.,
          'too_slow': 0.,
          'timed_out': 0.,
          'users': 10,
        })
        q2 = self._create_question()
        self._create_question_knowledge(q2, {
          'right': .7,
          'wrong': .3,
          'alternatives_right': 0.,
          'alternatives_wrong': 0.,
          'too_slow': 0.,
          'timed_out': 0.,
          'users': 10,
        })
        p = self.db.Play()
        p.users = [user2, computer]
        p.no_players = 2
        p.no_questions = 2
        p.finished = datetime.datetime.now() - datetime.timedelta(seconds=60 * 60 - 1)
        p.draw = True
        p.save()

        pq1a = self.db.PlayedQuestion()
        pq1a.play = p
        pq1a.question = q1
        pq1a.user = user2
        pq1a.right = True
        pq1a.answer = u'yes'
        pq1a.time = 1.0
        pq1a.save()

        pq1b = self.db.PlayedQuestion()
        pq1b.play = p
        pq1b.question = q1
        pq1b.user = computer
        pq1b.right = False
        pq1b.answer = u'wrong'
        pq1b.time = 1.0
        pq1b.save()

        pq2a = self.db.PlayedQuestion()
        pq2a.play = p
        pq2a.question = q2
        pq2a.user = user2
        pq2a.right = False
        pq2a.answer = u'wrong'
        pq2a.time = 2.0
        pq2a.save()

        pq2b = self.db.PlayedQuestion()
        pq2b.play = p
        pq2b.question = q2
        pq2b.user = computer
        pq2b.right = True
        pq2b.answer = u'yes'
        pq2b.time = 2.0
        pq2b.save()

        user, client, request = self._create_connected_client('peterbe')
        battle = client.current_client_battles[str(user._id)]
        battle.no_questions = 2
        client.on_message(dict(against_computer=1))

        self.assertTrue(client._sent[-3]['your_name'])
        self.assertTrue(client._sent[-2]['init_scoreboard'])
        self.assertTrue(client._sent[-1]['wait'])

        battle.min_wait_delay -= 3
        client.on_message(dict(next_question=1))

        self.assertTrue(client._sent[-3]['wait'])
        self.assertTrue(client._sent[-2]['question'])

        self.assertTrue(client._sent[-1]['bot_answers'])
        client.on_message(dict(alternatives=1))
        client.on_message(dict(answer='Yes'))


        self.assertTrue(client._sent[-3]['answered']['right'])
        self.assertTrue(client._sent[-2]['update_scoreboard'])
        self.assertTrue(client._sent[-1]['wait'])
        battle.min_wait_delay -= 3
        client.on_message(dict(next_question=1))
        self.assertTrue(client._sent[-2]['question'])



        return


        print client._sent[-1]
        print client2._sent[-1]


        return

        print client._sent[-3]
        print
        print client._sent[-2]
        print
        print client._sent[-1]

        return
        print client._sent[-3]
        print client2._sent[-3]
        print
        print client._sent[-2]
        print client2._sent[-2]
        print
        print client._sent[-1]
        print client2._sent[-1]
