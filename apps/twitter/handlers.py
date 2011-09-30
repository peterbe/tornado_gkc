from pymongo.objectid import InvalidId, ObjectId
import tornado.auth
from pprint import pformat
import tornado.web
from tornado.web import HTTPError
import logging

from apps.main.handlers import BaseAuthHandler, BaseHandler
from tornado_utils import djangolike_request_dict
from tornado_utils.routes import route
from tornado_utils.goo_gl import shorten as url_shorten
from utils import get_question_slug_url
from utils.decorators import login_required, login_redirect
from .forms import PostForm
import settings



class TwitterPostingsMixin(tornado.auth.TwitterMixin):

    ## necessary evil to be able to maintain two different twitter oauths
    def _oauth_consumer_token(self):
        self.require_setting("twitter_postings_consumer_key", "Twitter OAuth")
        self.require_setting("twitter_postings_consumer_secret", "Twitter OAuth")
        return dict(
            key=self.settings["twitter_postings_consumer_key"],
            secret=self.settings["twitter_postings_consumer_secret"])


@route('/twitter/auth/', name='twitter_auth')
class TwitterAuthHandler(BaseAuthHandler, TwitterPostingsMixin):

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


@route('/twitter/post/', name='twitter_manual_post')
class TwitterManualPost(BaseHandler, TwitterPostingsMixin):

    # not using the @login_redirect here because then I can't do
    # self.get(form=form) inside the post() method.
    def get(self, form=None):
        if not self.get_current_user():
            self.redirect(settings.LOGIN_URL)
            return
        options = self.get_base_options()
        if not self.is_admin_user(options['user']):
            raise HTTPError(403, "Not admin user")
        if form is None:
            message = ''
            if self.get_argument('published', None):
                _id = self.get_argument('published')
                message = self._create_message(_id)
                if len(message) > 140:
                    message = self._create_message(_id, use_url_shortener=True)
            form = PostForm(message=message)
        options['form'] = form
        options['page_title'] = "Manual Twitter Post"
        options['next_url'] = self.get_argument('next_url', None)
        self.render('twitter/post.html', **options)

    def _create_message(self, _id, use_url_shortener=False):
        question = self.db.Question.one({'_id': ObjectId(_id)})
        url = get_question_slug_url(question)
        url = 'http://%s%s' % (self.request.host, url)
        if use_url_shortener:

            url = url_shorten(url)
        message = "New question: %s\n%s" % (question.text, url)
        if question.genre and question.genre.approved:
            message += '\n#%s' % question.genre.name
        user_settings = self.get_user_settings(question.author)
        if user_settings and user_settings['twitter']:
            message += '\nThanks @%s' % user_settings['twitter']['screen_name']

        return message

    @tornado.web.asynchronous
    @login_redirect
    def post(self):
        user = self.get_current_user()
        if not self.is_admin_user(user):
            raise HTTPError(403, "Not admin user")

        data = djangolike_request_dict(self.request.arguments)
        form = PostForm(data)
        if form.validate():
            message = form.message.data
            next_url = self.get_argument('next_url', None)
            #self.finish(message)
            #return
            access_token = settings.TWITTER_KWISSLE_ACCESS_TOKENS[0]
            self.twitter_request(
                "/statuses/update",
                post_args={"status": message},
                access_token=access_token,
                callback=self.async_callback(lambda x: self._on_post(x, next_url=next_url)),
                next_url=next_url)
        else:
            self.get(form=form)

    def _on_post(self, new_entry, next_url=None):
        if not new_entry:
            # Call failed; perhaps missing permission?
            #self.authorize_redirect()
            logging.info(self.request.arguments)
            self.write("No new entry :(")
            return
        #from pprint import pprint
        #pprint(new_entry)
        twitter_url_tmpl = 'https://twitter.com/#!/%(username)s/status/%(id)s'
        twitter_url = twitter_url_tmpl % {
          'username': 'kwissle',
          'id': new_entry['id']
        }
        self.push_flash_message("Question published",
            '<a href="%s">On Twitter</a>' % twitter_url)

        if next_url:
            url = next_url
        else:
            url = self.reverse_url('review_accepted')

        logging.info("NEW_ENTRY=%s" % pformat(new_entry))
        self.redirect(url)
        #self.set_header("Content-Type", "text/plain")
        #logging.info("NEW_ENTRY=%r" % new_entry)
        #self.write("Posted a message!\n%s" % pformat(new_entry))
        #self.write(new_entry)
        #self.finish()
