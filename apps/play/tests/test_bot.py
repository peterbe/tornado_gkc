import unittest


from apps.play.bot import predict_bot_answer

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
