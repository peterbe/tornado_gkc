import datetime
from apps.main.models import BaseDocument, User
from apps.questions.models import Question

class Play(BaseDocument):
    __collection__ = 'plays'
    structure = {
      'users': [User],
      #'started': datetime.datetime,
      'no_players': int,
      'no_questions': int,
      'draw': bool,
      'winner': User
    }

    default_values = {
      'no_players': 0,
      'draw': False,
      #'started': datetime.datetime.now,
    }


class PlayedQuestion(BaseDocument):
    __collection__ = 'played_questions'
    structure = {
      'play': Play,
      'question': Question,
      'user': User,
      'right': bool,
      'answer': unicode,
      'alternatives': bool,
      'timed_out': bool,
    }

    default_values = {
      'right': False,
      'timed_out': False,
      'alternatives': False,
    }
