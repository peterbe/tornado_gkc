import datetime
from collections import defaultdict
from pymongo import ASCENDING, DESCENDING
from pymongo.objectid import InvalidId, ObjectId
import tornado.web
from tornado.web import HTTPError
from apps.main.handlers import BaseHandler
from utils.routes import route, route_redirect
import settings

route_redirect('/stats$', '/stats/')
@route('/stats/$', name='stats')
class StatsHandler(BaseHandler):
    def get(self):
        options = self.get_base_options()
        options['page_title'] = 'Statistics'
        self.render('stats/index.html', **options)

@route('/stats/login-method', name='stats_login_method')
class LoginMethodHandler(BaseHandler):
    def get(self):
        options = self.get_base_options()
        methods = defaultdict(int)
        total = 0
        for us in self.db.UserSettings.collection.find():
            if us['google']:
                methods['google'] += 1
            if us['twitter']:
                methods['twitter'] += 1
            if us['facebook']:
                methods['facebook'] += 1
            total += 1
        percentages = {}
        for t, n in methods.items():
            percentages[t] = int(100. * n / total)

        options['percentages'] = tornado.escape.json_encode(
          percentages
        )
        options['page_title'] = "Preferred login method"
        self.render('stats/login-method.html', **options)

class Getter(dict):
    def __getattr__(self, key):
        return self.get(key, None)#self.__getitem__(key)


@route('/stats/numbers', name='stats_numbers')
class NumbersHandler(BaseHandler):
    def get(self):
        options = self.get_base_options()
        facts = []

        facts.append(dict(label='Registered users',
                          number=self.db.User.find().count(),
                          url=self.reverse_url('stats_login_method')))

        facts.append(dict(label='Published questions',
                          number=self.db.Question
                            .find({'state':'PUBLISHED'}).count()))

        facts.append(dict(label='Questions pending review',
                          number=self.db.Question
                            .find({'state':'ACCEPTED'}).count(),
                          url=self.reverse_url('review_random')))

        facts.append(dict(label='Finished played games',
                          number=self.db.Play
                            .find({'finished':{'$ne':None}}).count()))

        facts.append(dict(label='Played questions',
                          number=self.db.PlayedQuestion
                            .find().count() / 2))

        options['facts'] = [Getter(x) for x in facts]
        options['page_title'] = "Numbers"
        self.render('stats/numbers.html', **options)
