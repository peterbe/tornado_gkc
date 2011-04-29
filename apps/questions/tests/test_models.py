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

        user_points = self.db.QuestionPoints()
        user_points.user = user
        user_points.points = 12
        user_points.save()

        user_points.update_highscore_position()
        self.assertEqual(user_points.highscore_position, 1)

        user2 = self.db.User()
        user2.username = u"else"
        user2.save()

        user_points2 = self.db.QuestionPoints()
        user_points2.user = user2
        user_points2.points = 10
        user_points2.save()

        user_points2.update_highscore_position()
        self.assertEqual(user_points2.highscore_position, 2)

        user_points2.points += 2
        user_points2.update_highscore_position()
        self.assertEqual(user_points2.highscore_position, 1)
        user_points.update_highscore_position()
        self.assertEqual(user_points.highscore_position, 1)

        user_points2.points += 1

        user_points2.update_highscore_position()
        self.assertEqual(user_points2.highscore_position, 2)
        user_points.update_highscore_position()
        self.assertEqual(user_points.highscore_position, 1)