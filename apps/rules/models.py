from pymongo.objectid import ObjectId
from apps.main.models import BaseDocument, User, register
from apps.questions.models import Genre

@register
class Rules(BaseDocument):
    __collection__ = 'rules'
    structure = {
      'name': unicode,
      'name_slug': unicode,
      'no_questions': int,
      'thinking_time': int,
      'genres': [ObjectId],
      'min_no_people': int,
      'max_no_people': int,
      'default': bool,
      'pictures_only': bool,
      'alternatives_only': bool,
      'must_register': bool,
      'author': ObjectId,
      'notes': unicode,
    }

    default_values = {
      'no_questions': 10,
      'thinking_time': 10,
      'default': False,
      'pictures_only': False,
      'alternatives_only': False,
      'must_register': False,
      'min_no_people': 2,
      'max_no_people': 2,
    }

    @property
    def genres(self):
        return self.db.Genre.find({'_id': {'$in': self['genres']}})

    @property
    def author(self):
        return self.db.User.find_one({'_id': self['author']})
