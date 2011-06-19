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

#class BaseTestCase(unittest.TestCase):
#    _once = False
#    def setUp(self):
#        if not self._once:
#            self._once = True
#            self.db = connection.test
#            self._emptyCollections()
#
#    def _emptyCollections(self):
#        [self.db.drop_collection(x) for x
#         in self.db.collection_names()
#         if x not in ('system.indexes',)]
#
#    def tearDown(self):
#        self._emptyCollections()
#        try:
#            del self.battles
#            del self.current_client_battles
#        except AttributeError:
#            pass
#

from apps.play.bot import predict_bot_answer

#class BotTestCase(BaseTestCase):
class BotTestCase(unittest.TestCase):

    def test_seconds_in_range(self):
        knowledge = {
          'right': 0.3,
          'wrong': 0.1,
          'alternatives_right': 0.1,
          'alternatives_wrong': 0.1,
          'too_slow': 0.3,
          'timed_out': 0.1,
          'users': 10,
        }

        for i in range(10):
            outcome = predict_bot_answer(10, knowledge)
            self.assertTrue(outcome['seconds'] >= 2)
            self.assertTrue(outcome['seconds'] <= 10)
