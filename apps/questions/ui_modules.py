from collections import defaultdict
from pprint import pprint
import tornado.web
from apps.questions.models import DIFFICULTIES

class RenderField(tornado.web.UIModule):
    def render(self, field):
        try:
            return field(title=field.description)
        except TypeError:
            return field()

class QuestionShortStats(tornado.web.UIModule):
    def render(self, question):
        db = question.db
        difficulties = {
          0: 0, # about right
          1: 0, # easy
          -1: 0 # hard
        }
        ratings = {
          0: 0, # ok
          1: 0, # good
          -1: 0 # bad
        }
        count = 0
        for review in db.QuestionReview.find({'question.$id': question._id}):
            difficulties[review['difficulty']] += 1
            rating = review['rating']
            if rating == 2: # legacy
                if isinstance(review.difficulty, float):
                    review.delete()
                    continue
                review.rating = 1
                review.save()
                rating = 1
            ratings[rating] += 1
            count += 1
        return dict(difficulties_json=tornado.escape.json_encode(difficulties),
                    ratings_json=tornado.escape.json_encode(ratings),
                    )
