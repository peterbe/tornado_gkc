import random
import datetime
import json
from collections import defaultdict
from apps.main.tests.base import BaseHTTPTestCase
import settings


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
        play.rules = self.default_rules_id
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

        self._create_question()
        self._create_question()
        self._create_question()

        play1 = self.db.Play()
        play1.rules = self.default_rules_id
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
        play2.rules = self.default_rules_id
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
        play.rules = self.default_rules_id
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
        self.assertEqual(play_message.play, play)

        flash_message = self.db.FlashMessage.one({'user.$id': user2._id})
        assert flash_message
        self.assertEqual(flash_message.text, u'hi!')

        # how render the replay page
        url = self.reverse_url('replay_play', play._id)
        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        self.assertTrue(u'hi!' in response.body)

    def test_highscore(self):
        user1 = self.db.User()
        user1.username = u'peterbe'
        user1.save()
        user2 = self.db.User()
        user2.username = u'chris'
        user2.save()
        computer = self.db.User()
        computer.username = settings.COMPUTER_USERNAME
        computer.save()

        pp1 = self.db.PlayPoints()
        pp1.rules = self.default_rules_id
        pp1.user = user1
        pp1.points = 20
        pp1.wins = 2
        pp1.losses = 3
        pp1.draws = 0
        pp1.save()
        pp1.update_highscore_position()
        self.assertEqual(pp1.highscore_position, 1)

        pp2 = self.db.PlayPoints()
        pp2.rules = self.default_rules_id
        pp2.user = user2
        pp2.points = 30
        pp2.wins = 3
        pp2.losses = 2
        pp2.draws = 0
        pp2.save()
        pp2.update_highscore_position()
        self.assertEqual(pp2.highscore_position, 1)
        pp1 = self.db.PlayPoints.one({'_id': pp1._id})
        self.assertEqual(pp1.highscore_position, 2)

        ppC = self.db.PlayPoints()
        ppC.user = computer
        ppC.points = 25
        ppC.wins = 3
        ppC.losses = 3
        ppC.draws = 0
        ppC.save()
        ppC.update_highscore_position()
        pp1 = self.db.PlayPoints.one({'_id': pp1._id})
        self.assertEqual(pp1.highscore_position, 2)
        pp2 = self.db.PlayPoints.one({'_id': pp2._id})
        self.assertEqual(pp2.highscore_position, 1)

        url = self.reverse_url('play_highscore')
        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        body = response.body
        self.assertTrue(-1 < body.find(user2.username)
                           < body.find(user1.username))
        self.assertTrue(computer.username not in body)


    def test_update_points_basic(self):
        url = self.reverse_url('play_update_points_json')
        response = self.client.get(url)
        self.assertEqual(response.code, 403)

        self._login()
        response = self.client.get(url)
        self.assertEqual(response.code, 400)

        response = self.client.get(url, {'play_id': 'xxx'})
        self.assertEqual(response.code, 404)

        user = self.db.User.one({'username': 'peterbe'})
        chris = self.db.User()
        chris.username = u'chris'
        chris.save()
#        bob = self.db.User()
#        bob.username = u'bob'
#        bob.save()
#        anon = self.db.User()
#        anon.username = u'anonymous123'
#        anon.anonymous = True
#        anon.save()
#        other_play = self._create_play([chris, bob])
#        response = self.client.get(url, {'play_id': str(other_play._id)})
#        self.assertEqual(response.code, 403)

        outcome = [
          (3, 0),
          (0, 1)
        ]
        play = self._create_play([user, chris], outcome=outcome)
        assert play.winner == user
        assert not play.draw
        response = self.client.get(url, {'play_id': play._id})
        self.assertEqual(response.code, 200)
        result = json.loads(response.body)

        pp = self.db.PlayPoints.one({'user.$id': user._id,
                                     'rules': self.default_rules_id})
        self.assertEqual(pp.points, 3)
        self.assertEqual(pp.wins, 1)
        self.assertEqual(pp.losses, 0)
        self.assertEqual(pp.draws, 0)

        self.assertEqual(result['highscore_position'], 1)
        self.assertEqual(result['highscore_position_before'], None)
        self.assertEqual(result['points_before'], 0)
        self.assertEqual(result['increment'], 3)
        self.assertEqual(result['increment'], 3)

        # run it once for the loser too
        self._login(username=u'chris')

        response = self.client.get(url, {'play_id': play._id})
        self.assertEqual(response.code, 200)
        result = json.loads(response.body)

        pp = self.db.PlayPoints.one({'user.$id': chris._id,
                                     'rules': self.default_rules_id})
        self.assertEqual(pp.points, 1)
        self.assertEqual(pp.wins, 0)
        self.assertEqual(pp.losses, 1)
        self.assertEqual(pp.draws, 0)

        self.assertEqual(result['highscore_position'], 2)
        self.assertEqual(result['highscore_position_before'], None)
        self.assertEqual(result['points_before'], 0)
        self.assertEqual(result['increment'], 1)
        self.assertEqual(result['increment'], 1)

    def test_update_points_one_anonymous(self):
        url = self.reverse_url('play_update_points_json')
        response = self.client.get(url)
        self.assertEqual(response.code, 403)

        self._login()
        response = self.client.get(url)
        self.assertEqual(response.code, 400)

        response = self.client.get(url, {'play_id': 'xxx'})
        self.assertEqual(response.code, 404)

        user = self.db.User.one({'username': 'peterbe'})
        anon = self.db.User()
        anon.username = u'anon'
        anon.anonymous = True
        anon.save()

        outcome = [
          (3, 0),
          (0, 1)
        ]
        play = self._create_play([user, anon], outcome=outcome)
        assert play.winner == user
        assert not play.draw
        response = self.client.get(url, {'play_id': play._id})
        self.assertEqual(response.code, 200)
        result = json.loads(response.body)

        pp = self.db.PlayPoints.one({'user.$id': user._id,
                                     'rules': self.default_rules_id})
        self.assertEqual(pp.points, 3)
        self.assertEqual(pp.wins, 1)
        self.assertEqual(pp.losses, 0)
        self.assertEqual(pp.draws, 0)

        self.assertEqual(result['highscore_position'], 1)
        self.assertEqual(result['highscore_position_before'], None)
        self.assertEqual(result['points_before'], 0)
        self.assertEqual(result['increment'], 3)
        self.assertEqual(result['increment'], 3)

        # run it once for the loser too
        self._login(username=u'anon')

        response = self.client.get(url, {'play_id': play._id})
        self.assertEqual(response.code, 200)
        result = json.loads(response.body)

        pp = self.db.PlayPoints.one({'user.$id': anon._id,
                                     'rules': self.default_rules_id})
        self.assertEqual(pp.points, 1)
        self.assertEqual(pp.wins, 0)
        self.assertEqual(pp.losses, 1)
        self.assertEqual(pp.draws, 0)

        self.assertEqual(result['highscore_position'], 2)
        self.assertEqual(result['highscore_position_before'], None)
        self.assertEqual(result['points_before'], 0)
        self.assertEqual(result['increment'], 1)
        self.assertEqual(result['increment'], 1)
        self.assertEqual(result['login_url'], self.reverse_url('login'))

    def test_update_points_one_anonymous_custom_rules(self):
        url = self.reverse_url('play_update_points_json')
        self._login()

        user = self.db.User.one({'username': 'peterbe'})
        anon = self.db.User()
        anon.username = u'anon'
        anon.anonymous = True
        anon.save()

        outcome = [
          (3, 0),
          (0, 1)
        ]
        own_rules = self.db.Rules()
        own_rules.no_questions = 2
        own_rules.author = user._id
        own_rules.save()

        play = self._create_play([user, anon], outcome=outcome,
                                 rules=own_rules)
        assert play.winner == user
        assert not play.draw
        response = self.client.get(url, {'play_id': play._id})
        self.assertEqual(response.code, 200)
        result = json.loads(response.body)

        pp = self.db.PlayPoints.one({'user.$id': user._id,
                                     'rules': own_rules._id})
        self.assertEqual(pp.points, 3)
        self.assertEqual(pp.wins, 1)
        self.assertEqual(pp.losses, 0)
        self.assertEqual(pp.draws, 0)

        self.assertEqual(result['highscore_position'], 1)
        self.assertEqual(result['highscore_position_before'], None)
        self.assertEqual(result['points_before'], 0)
        self.assertEqual(result['increment'], 3)
        self.assertEqual(result['increment'], 3)

        # run it once for the loser too
        self._login(username=u'anon')

        response = self.client.get(url, {'play_id': play._id})
        self.assertEqual(response.code, 200)
        result = json.loads(response.body)

        pp = self.db.PlayPoints.one({'user.$id': anon._id,
                                     'rules': own_rules._id})
        self.assertEqual(pp.points, 1)
        self.assertEqual(pp.wins, 0)
        self.assertEqual(pp.losses, 1)
        self.assertEqual(pp.draws, 0)

        self.assertEqual(result['highscore_position'], 2)
        self.assertEqual(result['highscore_position_before'], None)
        self.assertEqual(result['points_before'], 0)
        self.assertEqual(result['increment'], 1)
        self.assertEqual(result['increment'], 1)
        self.assertEqual(result['login_url'], self.reverse_url('login'))

    def test_update_points_one_anonymous_custom_rules_played_before(self):
        url = self.reverse_url('play_update_points_json')
        self._login()

        user = self.db.User.one({'username': 'peterbe'})
        anon = self.db.User()
        anon.username = u'Anon'
        anon.anonymous = True
        anon.save()

        user_pp = self.db.PlayPoints()
        user_pp.user = user
        user_pp.rules = self.default_rules_id
        user_pp.points = 10
        user_pp.wins = 1
        user_pp.losses = 1
        user_pp.draws = 1
        user_pp.highscore_position = 1
        user_pp.save()

        outcome = [
          (3, 0),
          (0, 1)
        ]
        own_rules = self.db.Rules()
        own_rules.no_questions = 2
        own_rules.author = user._id
        own_rules.save()

        play = self._create_play([user, anon], outcome=outcome,
                                 rules=own_rules)
        assert play.winner == user
        assert not play.draw
        response = self.client.get(url, {'play_id': play._id})
        self.assertEqual(response.code, 200)
        result = json.loads(response.body)

        pp = self.db.PlayPoints.one({'user.$id': user._id,
                                     'rules': own_rules._id})
        self.assertEqual(pp.points, 3)
        self.assertEqual(pp.wins, 1)
        self.assertEqual(pp.losses, 0)
        self.assertEqual(pp.draws, 0)

        self.assertEqual(result['highscore_position'], 1)
        self.assertEqual(result['highscore_position_before'], None)
        self.assertEqual(result['points_before'], 0)
        self.assertEqual(result['increment'], 3)
        self.assertEqual(result['increment'], 3)
        self.assertEqual(result['highscore_url'],
                         self.reverse_url('play_highscore_rules',
                                          own_rules._id))

        # run it once for the loser too
        self._login(username=u'Anon')

        response = self.client.get(url, {'play_id': play._id})
        self.assertEqual(response.code, 200)
        result = json.loads(response.body)

        pp = self.db.PlayPoints.one({'user.$id': anon._id,
                                     'rules': own_rules._id})
        self.assertEqual(pp.points, 1)
        self.assertEqual(pp.wins, 0)
        self.assertEqual(pp.losses, 1)
        self.assertEqual(pp.draws, 0)

        self.assertEqual(result['highscore_position'], 2)
        self.assertEqual(result['highscore_position_before'], None)
        self.assertEqual(result['points_before'], 0)
        self.assertEqual(result['increment'], 1)
        self.assertEqual(result['increment'], 1)
        self.assertEqual(result['login_url'], self.reverse_url('login'))

        # check the highscore page
        url = self.reverse_url('play_highscore_rules', own_rules._id)
        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        content = response.body.split('id="content_inner"')[1]
        self.assertTrue(-1 < content.find(user.username)
                           < content.find(anon.username))
