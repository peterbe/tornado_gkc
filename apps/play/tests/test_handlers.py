import datetime
from apps.main.tests.base import BaseHTTPTestCase, TestClient
from utils.http_test_client import TestClient

class HandlersTestCase(BaseHTTPTestCase):
    def test_starting_play(self):
        url = self.reverse_url('start_play')
        response = self.client.get(url)
        self.assertEqual(response.code, 302)
        self.assertTrue(self.reverse_url('play') in response.headers['location'])

    def test_play_homepage(self):
        url = self.reverse_url('play')
        response = self.client.get(url)
        self.assertEqual(response.code, 302)
        self.assertTrue('login' in response.headers['location'])

        self._login()
        response = self.client.get(url)
        self.assertEqual(response.code, 200)

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

    def test_replay_play(self):
        user1 = self.db.User()
        user1.username = u'peter'
        user1.save()
        user2 = self.db.User()
        user2.username = u'chris'
        user2.save()

        play = self.db.Play()
        play.users.extend([user1, user2])
        play.no_questions = 1
        play.no_players = 2
        play.started = datetime.datetime.now()
        play.finished = (datetime.datetime.now() +
                         datetime.timedelta(minutes=1.5))
        play.save()

        q1 = self._create_question(text='Is this first?')
        qp1a = self.db.PlayedQuestion()
        qp1a.play = play
        qp1a.question = q1
        qp1a.user = user1
        qp1a.right = True
        qp1a.answer = u'YEs'
        qp1a.save()

        qp1b = self.db.PlayedQuestion()
        qp1b.play = play
        qp1b.question = q1
        qp1b.user = user2
        qp1b.save()


        url = self.reverse_url('replay_play', play._id)
        response = self.client.get(url)
        self.assertEqual(response.code, 302)
        self.assertTrue('/login' in response.headers['location'])
        self._login()
        response = self.client.get(url)
        self.assertEqual(response.code, 403)
        self._login('peter')
        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        self.assertTrue('peter vs. chris' in response.body)
        self.assertTrue(q1.text in response.body)
        self.assertTrue(q1.answer in response.body)

        url = self.reverse_url('replay_play', '_'*24)
        response = self.client.get(url)
        self.assertEqual(response.code, 404)

        url = self.reverse_url('replay_play',
          ''.join(list(str(play._id))[::-1]))
        response = self.client.get(url)
        self.assertEqual(response.code, 404)

    def test_replays(self):
        url = self.reverse_url('play_replays')
        response = self.client.get(url)
        self.assertEqual(response.code, 302)
        self.assertTrue(self.reverse_url('login') + '?next='
                        in response.headers['Location'])

        self._login()
        response = self.client.get(url)
        self.assertEqual(response.code, 200)

        # make up a couple of plays
        user = self.db.User.one()
        assert user
        user1 = self.db.User()
        user1.username = u'peter'
        user1.save()
        user2 = self.db.User()
        user2.username = u'chris'
        user2.save()

        q1 = self._create_question()
        q2 = self._create_question()
        q3 = self._create_question()

        play1 = self.db.Play()
        play1.users = [user, user1]
        play1.no_players = 2
        play1.no_questions = 2
        then = datetime.datetime.now() + datetime.timedelta(days=1)
        play1.started = then
        play1.finished = then + datetime.timedelta(seconds=60)
        play1.winner = user1
        play1.save()

        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        replay_url = self.reverse_url('replay_play', play1._id)
        self.assertTrue(replay_url in response.body)

        play2 = self.db.Play()
        play2.users = [user2, user]
        play2.no_players = 2
        play2.no_questions = 2
        then = datetime.datetime.now() + datetime.timedelta(hours=1)
        play2.started = then
        play2.finished = then + datetime.timedelta(seconds=60)
        play2.winner = user
        play2.save()

        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        replay_url2 = self.reverse_url('replay_play', play2._id)
        self.assertTrue(replay_url2 in response.body)

        # most recent one first
        self.assertTrue(-1 < response.body.find(replay_url2) <
                             response.body.find(replay_url))

    def test_send_play_message(self):
        user1 = self.db.User()
        user1.username = u'peterbe'
        user1.save()
        user2 = self.db.User()
        user2.username = u'chris'
        user2.save()

        play = self.db.Play()
        play.users.extend([user1, user2])
        play.no_questions = 1
        play.no_players = 2
        play.started = datetime.datetime.now()
        play.finished = (datetime.datetime.now() +
                         datetime.timedelta(minutes=1.5))
        play.save()

        q1 = self._create_question()
        qp1a = self.db.PlayedQuestion()
        qp1a.play = play
        qp1a.question = q1
        qp1a.user = user1
        qp1a.right = True
        qp1a.answer = u'YEs'
        qp1a.save()

        qp1b = self.db.PlayedQuestion()
        qp1b.play = play
        qp1b.question = q1
        qp1b.user = user2
        qp1b.save()

        self._login()
        url = self.reverse_url('replay_play', play._id)
        response = self.client.get(url)
        self.assertEqual(response.code, 200)

        # there should now be a form viewable on there
        send_play_message_url = self.reverse_url('send_play_message',
                                                 play._id)
        self.assertTrue('action="%s"' % send_play_message_url in
                        response.body)
        response = self.client.post(send_play_message_url, {})
        self.assertEqual(response.code, 400)

        response = self.client.post(send_play_message_url,
                                    {'message': 'x'*101})
        self.assertEqual(response.code, 400)
        response = self.client.post(send_play_message_url,
                                    {'message': 'hi!'})
        self.assertEqual(response.code, 302)
        self.assertTrue(url in response.headers['Location'])

        play_message = self.db.PlayMessage.one()
        self.assertEqual(play_message.message, u'hi!')
        self.assertEqual(play_message['from'], user1)
        self.assertEqual(play_message['to'], user2)
        self.assertEqual(play_message.read, False)

        flash_message = self.db.FlashMessage.one({'user.$id': user2._id})
        assert flash_message
        self.assertEqual(flash_message.text, u'hi!')
