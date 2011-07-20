import datetime
from collections import defaultdict
from pprint import pprint
import tornado.web
from apps.main.models import connection
from apps.questions.models import DIFFICULTIES
from utils import dict_plus
import settings

from thumbnailer import ShowQuestionImageThumbnail
from thumbnailer import GetQuestionImageThumbnailSrc

class RenderField(tornado.web.UIModule):
    def render(self, field):
        try:
            return field(title=field.description)
        except TypeError:
            return field()

class QuestionShortStats(tornado.web.UIModule):
    def render(self, question):
        db = connection[settings.DATABASE_NAME]
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
        search = {'question.$id': question._id}
        for review in db.QuestionReview.collection.find(search):
            review = dict_plus(review)
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

        count = rights = alternatives = wrongs = tooslows = 0
        for qp in db.PlayedQuestion.collection.find(search):
            play = db.Play.collection.one({'_id': qp['play'].id})
            if not play:
                db.PlayedQuestion.collection.remove({'play.$id':qp['play'].id})
                continue

            if play['finished']:
                if qp['answer']:
                    count += 1
                    if qp['right']:
                        rights += 1
                    else:
                        wrongs += 1
                    if qp['alternatives']:
                        alternatives += 1
                else:
                    tooslows += 1

        answers = {
          'right': 0,
          'wrong': 0,
          'alternatives': 0,
        }
        if count:
            answers['right'] = int(100. * rights /count)
            answers['wrong'] = int(100. * wrongs /count)
            answers['alternatives'] = int(100. * alternatives /count)

        return dict(difficulties=difficulties,
                    ratings=ratings,
                    answers=answers,
                    )
        return dict(difficulties_json=tornado.escape.json_encode(difficulties),
                    ratings_json=tornado.escape.json_encode(ratings),
                    )

class ShowPercentage(tornado.web.UIModule):
    def render(self, p, sf=1):
        p = round(100 * p, sf)
        if sf:
            return '%s%%' % p
        else:
            return '%d%%' % p

class ShowAgeDays(tornado.web.UIModule):
    def render(self, date):
        d = datetime.datetime.today() - date
        return d.days
