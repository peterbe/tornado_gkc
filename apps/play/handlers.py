import tornado.web
from tornado.web import HTTPError
from apps.main.handlers import BaseHandler
from utils.routes import route, route_redirect
import settings

route_redirect('/play$', '/play/', name='play_redirect')
@route('/play/$', name='play')
class StartPlayingHandler(BaseHandler):

    @tornado.web.authenticated
    def get(self):
        options = self.get_base_options()
        user = self.get_current_user()
        node_url = settings.NODE_URL % \
          dict(host=settings.NODE_DOMAIN,
               name=user.username,
               uid=str(user._id),
               )
        node_url += '?u=%s' % user._id
        options['node_url'] = node_url
        #self.set_cookie('user_id', str(user._id))
        self.render("play/play.html", **options)
        #self.redirect(node_url)
