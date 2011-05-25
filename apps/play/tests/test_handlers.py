import datetime
from apps.main.tests.base import BaseHTTPTestCase, TestClient
from utils.http_test_client import TestClient

class HandlersTestCase(BaseHTTPTestCase):
    def test_starting_play(self):
        url = self.reverse_url('start_play')
        response = self.client.get(url)
        self.assertEqual(response.code, 302)
        self.assertTrue('login' in response.headers['location'])

        self._login()
        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        play_url = self.reverse_url('play')
        self.assertTrue(play_url in response.body)

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
