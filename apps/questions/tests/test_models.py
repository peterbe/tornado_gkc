from mongokit import RequireFieldError, ValidationError
import datetime
import unittest
from apps.questions.models import Question
from apps.main.tests.base import BaseModelsTestCase

class ModelsTestCase(BaseModelsTestCase):

    def test_create_question(self):
        pass
