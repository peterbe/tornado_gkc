import tornado.web
from tornado.web import HTTPError
from apps.main.handlers import BaseHandler
from utils.routes import route, route_redirect
import settings

route_redirect('/chat$', '/chat/', name='chat_redirect')
@route('/chat/$', name='chat')
class ChatHandler(BaseHandler):

    @tornado.web.authenticated
    def get(self):
        options = self.get_base_options()
        options['page_title'] = "Chat"
        self.render("chat/index.html", **options)
