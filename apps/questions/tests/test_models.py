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
