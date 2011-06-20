import datetime
from apps.play.models import PlayPoints
from base import BaseModelsTestCase


class ModelsTestCase(BaseModelsTestCase):

    def test_play(self):
        user1 = self.db.User()
        user1.username = u'peter'
        user1.save()

        play = self.db.Play()
        play.users.append(user1)
        play.no_players += 1
        play.no_questions = 10
        play.save()

        self.assertTrue(not play.draw)
        self.assertTrue(not play.winner)

    def test_update_highscore_position(self):
        user1 = self.db.User()
        user1.username = u'peter'
        user1.save()
        pp1 = self.db.PlayPoints()
        pp1.user = user1
        pp1.points = 0
        pp1.wins = 0
        pp1.losses = 0
        pp1.draws = 0
        pp1.save()

        user2 = self.db.User()
        user2.username = u'chris'
        user2.save()
        pp2 = self.db.PlayPoints()
        pp2.user = user2
        pp2.points = 10
        pp2.wins = 2
        pp2.losses = 0
        pp2.draws = 1
        pp2.save()

        user3 = self.db.User()
        user3.username = u'ashley'
        user3.save()
        pp3 = self.db.PlayPoints()
        pp3.user = user3
        pp3.points = 8
        pp3.wins = 1
        pp3.losses = 2
        pp3.draws = 0
        pp3.save()

        pp3.update_highscore_position()
        self.assertEqual(pp3.highscore_position, 2)
        pp2 = self.db.PlayPoints.one({'_id': pp2._id})
        self.assertEqual(pp2.highscore_position, 1)
        pp1 = self.db.PlayPoints.one({'_id': pp1._id})
        self.assertEqual(pp1.highscore_position, None)

        user4 = self.db.User()
        user4.username = u'matt'
        user4.save()
        pp4 = self.db.PlayPoints()
        pp4.user = user4
        pp4.points = 8
        pp4.wins = 1
        pp4.losses = 2
        pp4.draws = 0
        pp4.save()

        pp4.update_highscore_position()
        self.assertEqual(pp4.highscore_position, 2)
        pp3 = self.db.PlayPoints.one({'_id': pp3._id})
        self.assertEqual(pp3.highscore_position, 2)
        pp2 = self.db.PlayPoints.one({'_id': pp2._id})
        self.assertEqual(pp2.highscore_position, 1)
        pp1 = self.db.PlayPoints.one({'_id': pp1._id})
        self.assertEqual(pp1.highscore_position, None)

        pp4.points += 2
        pp4.save()

        pp4.update_highscore_position()
        self.assertEqual(pp4.highscore_position, 1)
        pp3 = self.db.PlayPoints.one({'_id': pp3._id})
        self.assertEqual(pp3.highscore_position, 2)
        pp2 = self.db.PlayPoints.one({'_id': pp2._id})
        self.assertEqual(pp2.highscore_position, 1)
        pp1 = self.db.PlayPoints.one({'_id': pp1._id})
        self.assertEqual(pp1.highscore_position, None)

        pp4.points += 1
        pp4.save()

        pp4.update_highscore_position()
        self.assertEqual(pp4.highscore_position, 1)
        pp3 = self.db.PlayPoints.one({'_id': pp3._id})
        self.assertEqual(pp3.highscore_position, 3)
        pp2 = self.db.PlayPoints.one({'_id': pp2._id})
        self.assertEqual(pp2.highscore_position, 2)
        pp1 = self.db.PlayPoints.one({'_id': pp1._id})
        self.assertEqual(pp1.highscore_position, None)

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


    def test_calculate_play_points(self):
        user1 = self.db.User()
        user1.username = u'peter'
        user1.save()

        user2 = self.db.User()
        user2.username = u'chris'
        user2.save()

        q1 = self._create_question()
        q2 = self._create_question()
        q3 = self._create_question()

        # play1 unfinished
        play1 = self.db.Play()
        play1.users = [user1, user2]
        play1.no_players = 2
        play1.no_questions = 3
        play1.started = datetime.datetime.now()
        play1.halted = datetime.datetime.now() + datetime.timedelta(seconds=1)
        play1.save()

        # play2 user1 one right and user2 two right on alternatives
        play2 = self.db.Play()
        play2.users = [user1, user2]
        play2.no_players = 2
        play2.no_questions = 3
        play2.started = datetime.datetime.now()
        play2.finished = datetime.datetime.now() + datetime.timedelta(seconds=1)
        play2.save()

        # question 1 - user 1 get it right
        pq1 = self.db.PlayedQuestion() ; pq2 = self.db.PlayedQuestion()
        pq1.play = play2               ; pq2.play = play2
        pq1.question = q1              ; pq2.question = q1
        pq1.user = user1               ; pq2.user = user2
        pq1.right = True               ; pq2.right = False
        pq1.answer = u'Yes'            ; pq2.answer = u'Wrong'
        pq1.save()                     ; pq2.save()

        # question 1 - user 2 gets it right after alternatives
        pq1 = self.db.PlayedQuestion() ; pq2 = self.db.PlayedQuestion()
        pq1.play = play2               ; pq2.play = play2
        pq1.question = q2              ; pq2.question = q2
        pq1.user = user1               ; pq2.user = user2
        pq1.right = False              ; pq2.right = True
        pq1.answer = None              ; pq2.answer = u'Yes'
        None                           ; pq2.alternatives = True
        pq1.save()                     ; pq2.save()

        # question 1 - user 2 gets it right after alternatives
        pq1 = self.db.PlayedQuestion() ; pq2 = self.db.PlayedQuestion()
        pq1.play = play2               ; pq2.play = play2
        pq1.question = q3              ; pq2.question = q3
        pq1.user = user1               ; pq2.user = user2
        pq1.right = False              ; pq2.right = True
        pq1.answer = u'wrong'          ; pq2.answer = u'Yes'
        pq1.alternatives = True        ; pq2.alternatives = True
        pq1.save()                     ; pq2.save()

        play2.winner = user1
        play2.save()

        user1_play_points = PlayPoints.calculate(user1)
        self.assertEqual(user1_play_points.wins, 1)
        self.assertEqual(user1_play_points.losses, 0)
        self.assertEqual(user1_play_points.draws, 0)
        self.assertEqual(user1_play_points.points, 3)

        user2_play_points = PlayPoints.calculate(user2)
        self.assertEqual(user2_play_points.wins, 0)
        self.assertEqual(user2_play_points.losses, 1)
        self.assertEqual(user2_play_points.draws, 0)
        self.assertEqual(user2_play_points.points, 2)


        # play3 user1 one right and user2 one right
        play3 = self.db.Play()
        play3.users = [user1, user2]
        play3.no_players = 2
        play3.no_questions = 2
        play3.started = datetime.datetime.now()
        play3.finished = datetime.datetime.now() + datetime.timedelta(seconds=1)
        play3.save()

        # question 1 - user 1 get it right
        pq1 = self.db.PlayedQuestion() ; pq2 = self.db.PlayedQuestion()
        pq1.play = play3               ; pq2.play = play3
        pq1.question = q1              ; pq2.question = q1
        pq1.user = user1               ; pq2.user = user2
        pq1.right = True               ; pq2.right = False
        pq1.answer = u'Yes'            ; pq2.answer = u'Wrong'
        pq1.save()                     ; pq2.save()

        # question 1 - user 2 gets it right after alternatives
        pq1 = self.db.PlayedQuestion() ; pq2 = self.db.PlayedQuestion()
        pq1.play = play3               ; pq2.play = play3
        pq1.question = q2              ; pq2.question = q2
        pq1.user = user1               ; pq2.user = user2
        pq1.right = False              ; pq2.right = True
        pq1.answer = None              ; pq2.answer = u'Yes'
        None                           ; pq2.alternatives = False
        pq1.save()                     ; pq2.save()

        play3.draw = True
        play3.save()
