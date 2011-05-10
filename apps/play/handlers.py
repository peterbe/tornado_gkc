import tornado.web
from tornado.web import HTTPError
from apps.main.handlers import BaseHandler
from utils.routes import route, route_redirect
import settings

route_redirect('/play/start$', '/play/start/', name='start_play_redirect')
@route('/play/start/$', name='start_play')
class StartPlayingHandler(BaseHandler):

    @tornado.web.authenticated
    def get(self):
        options = self.get_base_options()
        iframe_url = self.reverse_url('play')
        options['iframe_url'] = iframe_url
        #self.set_cookie('user_id', str(user._id))
        self.render("play/start_play.html", **options)

@route('/play/$', name='play')
class PlayHandler(BaseHandler):

    @tornado.web.authenticated
    def get(self):
        options = self.get_base_options()
        user = self.get_current_user()
        config = {
          'SOCKET_PORT': 8888,
          'HIGHSCORE_URL': '/play/highscore/',
          'HOMEPAGE_URL': '/',
          'DEBUG': self.application.settings['debug'],
        }
        options['config_json'] = tornado.escape.json_encode(config)
        self.render("play/play.html", **options)
