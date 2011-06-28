import datetime
from apps.main.models import BaseDocument, User, register

@register
class Genre(BaseDocument):
    __collection__ = 'question_genres'
    structure = {
      'name': unicode,
      'approved': bool,
    }

    default_values = {
      'approved': False,
    }


DRAFT = u"DRAFT"
SUBMITTED = u"SUBMITTED"
REJECTED = u"REJECTED"
ACCEPTED = u"ACCEPTED"
PUBLISHED = u"PUBLISHED"
STATES = DRAFT, SUBMITTED, REJECTED, ACCEPTED, PUBLISHED

EASY = u"EASY"
MEDIUM = u"MEDIUM"
HARD = u"HARD"
DIFFICULTIES = EASY, MEDIUM, HARD

@register
class Question(BaseDocument):
    __collection__ = 'questions'
    structure = {
      'text': unicode,
      'answer': unicode,
      'accept': [unicode],
      'alternatives': [unicode],
      'genre': Genre,
      'spell_correct': bool,
      'difficulty': unicode,
      'language': unicode,
      'comment': unicode,
      'author': User,
      'state': unicode, # e.g. 'PUBLISHED'
      'submit_date': datetime.datetime,
      'reject_date': datetime.datetime,
      'reject_comment': unicode,
      'accept_date': datetime.datetime,
      'publish_date': datetime.datetime,
    }

    #indexes = [
    #  {'fields': 'state'},
    #]

    validators = {
      'state': lambda x: x in STATES,
      'difficulty': lambda x: x in DIFFICULTIES,
    }

    default_values = {
      'state': STATES[0],
      'difficulty': MEDIUM,
      'language': u'en-gb',
    }

    def has_image(self):
        return bool(self.db.QuestionImage
                     .find({'question.$id': self._id})
                     .count())

    def get_image(self):
        return self.db.QuestionImage.one({'question.$id': self._id})


@register
class QuestionImage(BaseDocument):
    __collection__ = 'question_images'
    structure = {
      'question': Question,
    }
    gridfs = {'files':['original']}

#OK = u"OK"
VERIFIED = u"VERIFIED"
UNSURE = u"UNSURE"
WRONG = u"WRONG"
TOO_EASY = u"TOO EASY"
TOO_HARD = u"TOO HARD"
VERDICTS = VERIFIED, UNSURE, WRONG, TOO_EASY, TOO_HARD

@register
class QuestionReview(BaseDocument):
    __collection__ = 'question_reviews'
    structure = {
      'question': Question,
      'user': User,
      'verdict': unicode,
      'difficulty': int,
      'rating': int,
      'comment': unicode,
    }

    validators = {
      'verdict': lambda x: x in VERDICTS
    }


@register
class QuestionPoints(BaseDocument):
    __collection__ = 'question_points'
    structure = {
      'user': User,
      'points': int,
      'highscore_position': int,
    }

    default_values = {
      'highscore_position': 0,
    }
    required_fields = ['user','points']
    validators = {
    }

    def update_highscore_position(self):
        # how many has better points?
        c = self.db.QuestionPoints.find({'points':{'$gte': self.points}}).count()
        self.highscore_position = max(c, 1)
        self.save()

        self.db.QuestionPoints.collection.update(
          {'points':{'$lt': self.points}},
          {'$inc': {'highscore_position': 1}},
          multi=True # multi
        )


@register
class QuestionKnowledge(BaseDocument):
    __collection__ = 'question_knowledge'
    structure = {
      'question': Question,
      'right': float,
      'wrong': float,
      'alternatives_right': float,
      'alternatives_wrong': float,
      'too_slow': float,
      'timed_out': float,
      'users': int,
    }

    default_values = {
      'users': 0,
      'right': 0.0,
      'wrong': 0.0,
      'alternatives_right': 0.0,
      'alternatives_wrong': 0.0,
      'too_slow': 0.0,
      'timed_out': 0.0,
    }
