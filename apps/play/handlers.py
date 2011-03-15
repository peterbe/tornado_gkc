#from pymongo.objectid import InvalidId, ObjectId
#import re
#from random import randint
#from pprint import pprint
import tornado.web
from tornado.web import HTTPError
#from utils.decorators import login_required
from apps.main.handlers import BaseHandler
from utils.routes import route, route_redirect
import settings
#from models import *
#from forms import QuestionForm

@route('/play/?$', name='play')
class StartPlayingHandler(BaseHandler):

    def get(self):

        user = self.get_current_user()
        node_url = settings.NODE_URL % \
          dict(host='gkc',
               name=user.username,
               uid=str(user._id),
               )
        self.set_cookie('user_id', str(user._id))
        #self.write(node_url)
        self.redirect(node_url)
