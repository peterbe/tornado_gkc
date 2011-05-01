from mongokit import RequireFieldError, ValidationError
import datetime
import unittest
from apps.questions.models import Question, STATES
from base import BaseModelsTestCase

class ModelsTestCase(BaseModelsTestCase):

    def test_draft_by_default(self):
        user = self.db.User()
        user.username = u"something"
        user.save()
        question = self.db.Question()

        question.text = u"Who wrote what?"
        question.answer = u"Dickens"
        question.accept = [u"Charles Dickens"]
        question.alternatives = [u"Dickens", u"One", u"Two", u"Three"]
        question.spell_check = True
        question.comment = u"Some Comment"
        genre = self.db.Genre()
        genre.name = u"Lit"
        genre.save()
        question.genre = genre
        question.author = user
        question.save()
        self.assertEqual(question.state, STATES[0])


    def test_questionpoints_highscore(self):
        user = self.db.User()
        user.username = u"something"
        user.save()

        question_points = self.db.QuestionPoints()
        question_points.user = user
        question_points.points = 12
        question_points.save()

        question_points.update_highscore_position()
        self.assertEqual(question_points.highscore_position, 1)

        user2 = self.db.User()
        user2.username = u"else"
        user2.save()

        question_points2 = self.db.QuestionPoints()
        question_points2.user = user2
        question_points2.points = 10
        question_points2.save()

        question_points2.update_highscore_position()
        self.assertEqual(question_points2.highscore_position, 2)
        question_points = self.db.QuestionPoints.one({'_id': question_points._id})
        self.assertEqual(question_points.highscore_position, 1)

        question_points2.points += 2
        question_points2.update_highscore_position()
        self.assertEqual(question_points2.highscore_position, 1)
        question_points = self.db.QuestionPoints.one({'_id': question_points._id})
        self.assertEqual(question_points.highscore_position, 1)

        question_points2.points += 1

        question_points2.update_highscore_position()
        self.assertEqual(question_points2.highscore_position, 1)
        question_points = self.db.QuestionPoints.one({'_id': question_points._id})
        #question_points.update_highscore_position()
        self.assertEqual(question_points.highscore_position, 2)

    def test_questionpoints_highscore_basic(self):
        user = self.db.User()
        user.username = u"one"
        user.save()
        qp = self.db.QuestionPoints()
        qp.user = user
        qp.points = 12
        qp.highscore_position = 2
        qp.save()

        user2 = self.db.User()
        user2.username = u"two"
        user2.save()
        qp = self.db.QuestionPoints()
        qp.user = user2
        qp.points = 24
        qp.highscore_position = 1
        qp.save()

        user3 = self.db.User()
        user3.username = u"three"
        user3.save()
        qp = self.db.QuestionPoints()
        qp.user = user3
        qp.points = 6
        qp.highscore_position = 3
        qp.save()

        user4 = self.db.User()
        user4.username = u"four"
        user4.save()
        qp = self.db.QuestionPoints()
        qp.user = user4
        qp.points = 20
        qp.save()
        qp.update_highscore_position()

        order = []
        for each in self.db.QuestionPoints.find().sort('highscore_position'):
            order.append((each.highscore_position,
                          each.user.username))
        # remember,
        self.assertEqual(order,
                         [(1, "two"),
                          (2, "four"),
                          (3, "one"),
                          (4, "three")])
