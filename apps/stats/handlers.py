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
class StatsHandler(BaseHandler):
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
