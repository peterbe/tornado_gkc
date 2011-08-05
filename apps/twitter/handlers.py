import tornado.auth
import tornado.web
from tornado.web import HTTPError

from apps.main.handlers import BaseAuthHandler, BaseHandler
from utils.routes import route, route_redirect
from utils.decorators import login_required, login_redirect


@route('/twitter/auth/', name='twitter_auth')
class TwitterAuthHandler(BaseAuthHandler, tornado.auth.TwitterMixin):

    @tornado.web.asynchronous
    @login_redirect
    def get(self):
        user = self.get_current_user()
        if not self.is_admin_user(user):
            raise HTTPError(403, "Only for the administrators")

        if self.get_argument("oauth_token", None):
            self.get_authenticated_user(self.async_callback(self._on_auth))
            return
        self.authenticate_redirect()

    def _on_auth(self, user_struct):
        if not user_struct:
            raise HTTPError(500, "Twitter auth failed")
        from pprint import pprint
        pprint(user_struct)
        #if not user_struct.get('email'):
        #    raise HTTPError(500, "No email provided")
        #print user_struct
        access_token = user_struct['access_token']['key']
        self.write(str(user_struct))
        self.finish()

    ## necessary evil to be able to maintain two different twitter oauths
    def _oauth_consumer_token(self):
        self.require_setting("twitter_postings_consumer_key", "Twitter OAuth")
        self.require_setting("twitter_postings_consumer_secret", "Twitter OAuth")
        return dict(
            key=self.settings["twitter_postings_consumer_key"],
            secret=self.settings["twitter_postings_consumer_secret"])


@route('/twitter/post/', name='twitter_manual_post')
class TwitterManualPost(BaseHandler):

    @login_redirect
    def get(self):
        options = self.get_base_options()
        if not self.is_admin_user(options['user']):
            raise HTTPError(403, "Not admin user")

        options['page_title'] = "Manual Twitter Post"
        self.render('twitter/post.html', **options)
