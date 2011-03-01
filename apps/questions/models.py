import datetime
from apps.main.models import BaseDocument, User

class Genre(BaseDocument):
    __collection__ = 'question_genres'
    structure = {
      'name': unicode,
    }


DRAFT = u"DRAFT"
SUBMITTED = u"SUBMITTED"
REJECTED = u"REJECTED"
ACCEPTED = u"ACCEPTED"
PUBLISHED = u"PUBLISHED"
STATES = DRAFT, SUBMITTED, REJECTED, ACCEPTED, PUBLISHED


class Question(BaseDocument):
    __collection__ = 'questions'
    structure = {
      'text': unicode,
      'answer': unicode,
      'accept': [unicode],
      'alternatives': [unicode],
      'genre': Genre,
      'spell_correct': bool,
      'comment': unicode,
      'author': User,
      'state': unicode, # e.g. 'PUBLISHED'
      'submit_date': datetime.datetime,
      'reject_date': datetime.datetime,
      'reject_comment': unicode,
      'accept_date': datetime.datetime,
      'publish_date': datetime.datetime,
    }

    indexes = [
      {'fields': 'state'},
    ]

    validators = {
      'state': lambda x: x in STATES
    }

    default_values = {
      'state': STATES[0],
    }



#OK = u"OK"
VERIFIED = u"VERIFIED"
UNSURE = u"UNSURE"
WRONG = u"WRONG"
TOO_EASY = u"TOO EASY"
TOO_HARD = u"TOO HARD"
VERDICTS = VERIFIED, UNSURE, WRONG, TOO_EASY, TOO_HARD

class QuestionReview(BaseDocument):
    __collection__ = 'question_reviews'
    structure = {
      'question': Question,
      'user': User,
      'verdict': unicode,
      'rating': int,
      'comment': unicode,
    }

    validators = {
      'verdict': lambda x: x in VERDICTS
    }
