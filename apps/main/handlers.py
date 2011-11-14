# python
import xml.etree.cElementTree as etree
#from xml.etree.cElementTree import Element, SubElement, tostring
import stat
import traceback
import httplib
from hashlib import md5
from cStringIO import StringIO
from urlparse import urlparse
from pprint import pprint
from collections import defaultdict
from pymongo.objectid import InvalidId, ObjectId
from time import mktime, sleep, time
import datetime
from urllib import quote, urlencode
import os.path
import re
import logging

# tornado
import tornado.gen
import tornado.httpclient
import tornado.auth
import tornado.web
from tornado.web import HTTPError

# app
from tornado_utils.routes import route
from models import *
from tornado_utils.send_mail import send_email
from utils.decorators import login_required, login_redirect
from tornado_utils import parse_datetime, niceboolean, \
  DatetimeParseError, valid_email, random_string, \
  all_hash_tags, all_atsign_tags, generate_random_color
from utils import get_question_slug_url
from forms import SettingsForm
import settings

from apps.questions.models import ACCEPTED, PUBLISHED
#from config import *


def title_to_tags(title):
    return list(set([x[1:] for x in re.findall(r'\B[@#][\w\-\.]+', title, re.U)]))

class HTTPSMixin(object):

    def is_secure(self):
        # XXX is this really the best/only way?
        return self.request.headers.get('X-Scheme') == 'https'

    def httpify_url(self):
        return self.request.full_url().replace('https://', 'http://')

    def httpsify_url(self):
        return self.request.full_url().replace('http://', 'https://')


class BaseHandler(tornado.web.RequestHandler, HTTPSMixin):

    def static_url(self, path):
        self.require_setting("static_path", "static_url")
        if not hasattr(BaseHandler, "_static_timestamps"):
            BaseHandler._static_timestamps = {}
        timestamps = BaseHandler._static_timestamps
        abs_path = os.path.join(self.application.settings["static_path"],
                                        path)
        if abs_path not in timestamps:
            try:
                timestamps[abs_path] = os.stat(abs_path)[stat.ST_MTIME]
            except OSError:
                logging.error("Could not open static file %r", path)
                timestamps[abs_path] = None
        base = self.request.protocol + "://" + self.request.host \
            if getattr(self, "include_host", False) else ""
        static_url_prefix = self.settings.get('static_url_prefix', '/static/')
        if timestamps.get(abs_path):
            if self.settings.get('embed_static_url_timestamp', False):
                return base + static_url_prefix + 'v-%d/' % timestamps[abs_path] + path
            else:
                return base + static_url_prefix + path + "?v=%d" % timestamps[abs_path]
        else:
            return base + static_url_prefix + path

    page_not_found_page_title = "Page not found :("

    def send_page_not_found(self, message=None):
        options = self.get_base_options()
        options['page_title'] = self.page_not_found_page_title
        options['message'] = message
        self.set_status(404)
        self.render('404.html', **options)

    def _handle_request_exception(self, exception):
        if not isinstance(exception, HTTPError) and \
          not self.application.settings['debug']:
            # ie. a 500 error
            try:
                self._email_exception(exception)
            except:
                print "** Failing even to email exception **"

        if isinstance(exception, HTTPError) and exception.status_code == 404:
            self.send_page_not_found(message=exception.log_message)
            return

        if self.application.settings['debug']:
            # Because of
            # https://groups.google.com/d/msg/python-tornado/Zjv6_3OYaLs/CxkC7eLznv8J
            print "Exception!"
            print exception

        super(BaseHandler, self)._handle_request_exception(exception)

    def _log(self):
        """overwritten from tornado.web.RequestHandler because we want to put
        all requests as logging.debug and keep all normal logging.info()"""
        if self._status_code < 400:
            #log_method = logging.info
            log_method = logging.debug
        elif self._status_code < 500:
            log_method = logging.warning
        else:
            log_method = logging.error
        request_time = 1000.0 * self.request.request_time()
        log_method("%d %s %.2fms", self._status_code,
                   self._request_summary(), request_time)


    def _email_exception(self, exception): # pragma: no cover
        import sys
        from pprint import pprint
        err_type, err_val, err_traceback = sys.exc_info()
        error = u'%s: %s' % (err_type, err_val)
        out = StringIO()
        subject = "%r on %s" % (err_val, self.request.path)
        print >>out, "TRACEBACK:"
        traceback.print_exception(err_type, err_val, err_traceback, 500, out)
        traceback_formatted = out.getvalue()
        print traceback_formatted
        print >>out, "\nREQUEST ARGUMENTS:"
        arguments = self.request.arguments
        if arguments.get('password') and arguments['password'][0]:
            password = arguments['password'][0]
            arguments['password'] = password[:2] + '*' * (len(password) -2)
        pprint(arguments, out)

        print >>out, "\nCOOKIES:"
        for cookie in self.cookies:
            print >>out, "  %s:" % cookie,
            print >>out, repr(self.get_secure_cookie(cookie))

        print >>out, "\nREQUEST:"
        for key in ('full_url', 'protocol', 'query', 'remote_ip',
                    'request_time', 'uri', 'version'):
            print >>out, "  %s:" % key,
            value = getattr(self.request, key)
            if callable(value):
                try:
                    value = value()
                except:
                    pass
            print >>out, repr(value)

        print >>out, "\nGIT REVISION: ",
        print >>out, self.application.settings['git_revision']

        print >>out, "\nHEADERS:"
        pprint(dict(self.request.headers), out)
        try:
            send_email(self.application.settings['email_backend'],
                   subject,
                   out.getvalue(),
                   self.application.settings['webmaster'],
                   settings.DEVELOPER_EMAILS,
                   )
        except:
            logging.error("Failed to send email",
                          exc_info=True)

    @property
    def db(self):
        return self.application.con[self.application.database_name]

    def get_current_user(self):
        # the 'user' cookie is for securely logged in people
        user_id = self.get_secure_cookie("user")
        if user_id:
            return self.db.User.one({'_id': ObjectId(user_id)})

    def get_user_settings(self, user, fast=False):
        return self.get_current_user_settings(user=user, fast=fast)

    def get_newsletter_settings(self, user, fast=False):
        if fast:
            conn = self.db.NewsletterSettings.collection
        else:
            conn = self.db.NewsletterSettings
        return conn.one({'user': user._id})

    # shortcut where the user parameter is not optional
    def get_current_user_settings(self,
                                  user=None,
                                  fast=False,
                                  create_if_necessary=False):
        if user is None:
            user = self.get_current_user()

        if not user:
            raise ValueError("Can't get settings when there is no user")
        _search = {'user': user['_id']}
        if fast:
            return self.db.UserSettings.collection.one(_search) # skip mongokit
        else:
            user_settings = self.db.UserSettings.one(_search)
            if create_if_necessary and not user_settings:
                user_settings = self.db.UserSettings()
                user_settings.user = user['_id']
                user_settings.save()
            return user_settings

    def create_user_settings(self, user, **default_settings):
        user_settings = self.db.UserSettings()
        user_settings.user = user['_id']
        for key in default_settings:
            setattr(user_settings, key, default_settings[key])
        user_settings.save()
        return user_settings

    def get_cdn_prefix(self):
        """return something that can be put in front of the static filename
        E.g. if filename is '/static/image.png' and you return '//cloudfront.com'
        then final URL presented in the template becomes
        '//cloudfront.com/static/image.png'
        """
        return self.application.settings.get('cdn_prefix')
        # at the time of writing, I'm just going to use the CDN if you're running
        # a secure connection. This is because the secure connection is limited
        # to paying customers and they deserve it
        if self.is_secure():
            return self.application.settings.get('cdn_prefix')

    def write_json(self, struct, javascript=False):
        if javascript:
            self.set_header("Content-Type", "text/javascript; charset=UTF-8")
        else:
            self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.write(tornado.escape.json_encode(struct))

    def write_jsonp(self, callback, struct):
        self.set_header("Content-Type", "text/javascript; charset=UTF-8")
        self.write('%s(%s)' % (callback, tornado.escape.json_encode(struct)))

    def serialize_dict(self, data):
        for key, value in data.items():
            if isinstance(value, (datetime.datetime, datetime.date)):
                data[key] = mktime(value.timetuple())
        return data

    def find_user(self, username):
        return self.db.User.one(dict(username=\
         re.compile('^%s$' % re.escape(username), re.I)))

    def find_user_by_email(self, email):
        return self.db.User.one(dict(email=\
         re.compile('^%s$' % re.escape(email), re.I)))

    def has_user(self, username):
        return bool(self.find_user(username))

    def is_admin_user(self, user):
        return user.email in settings.ADMIN_EMAILS

    def get_base_options(self):
        # The templates rely on these variables
        options = dict(user=None,
                       user_name=None,
                       is_admin_user=False,
                       PROJECT_TITLE=settings.PROJECT_TITLE,
                       page_title=settings.PROJECT_TITLE,
                       #total_question_points=0,
                       total_play_points=0,
                       )

        # default settings
        settings_ = dict(
                        disable_sound=False,
                        )

        user = self.get_current_user()
        user_name = None

        if user:
            if self.get_secure_cookie('user'):
                options['user'] = user
                options['is_admin_user'] = self.is_admin_user(user)
                if user.first_name:
                    user_name = user.first_name
                elif user.email:
                    user_name = user.email
                else:
                    user_name = user.username
                options['user_name'] = user_name

            # override possible settings
            user_settings = self.get_current_user_settings(user)
            #options['total_question_points'] = \
            #  self.get_total_question_points(user)
            play_points = self.get_play_points(user)
            if play_points:
                options['total_play_points'] = play_points.points
                if not play_points.highscore_position:
                    play_points.update_highscore_position()
                options['play_highscore_position'] = play_points.highscore_position
            else:
                options['total_play_points'] = None
                options['play_highscore_position'] = None

        options['settings'] = settings_

        options['git_revision'] = self.application.settings['git_revision']
        options['debug'] = self.application.settings['debug']

        return options

    def push_flash_message(self, title, text='', user=None):
        if user is None:
            user = self.get_current_user()
            if not user:
                return
        if not text:
            raise ValueError("AT the moment we can't accept blank texts on flash "\
                             "messages because gritter won't be able to show it")
        for msg in self.db.FlashMessage.collection.find({'user':user._id})\
          .sort('add_date', -1).limit(1):
            if msg['title'] == title and msg['text'] == text:
                # but was it several seconds ago?
                if (datetime.datetime.now() - msg['add_date']).seconds < 3:
                    return
        msg = self.db.FlashMessage()
        msg.user = user._id
        msg.title = unicode(title)
        msg.text = unicode(text)
        msg.save()

    def pull_flash_messages(self, unread=True, user=None):
        if user is None:
            user = self.get_current_user()
            if not user:
                return []
        _search = {'user':user._id}
        if unread:
            _search['read'] = False
        return self.db.FlashMessage.find(_search).sort('add_date', 1)

    def get_play_points(self, user, rules_id=None):
        """return the total play points or None"""
        if rules_id is None:
            rules_id = self.db.Rules.one({'default': True})._id
            #default_rules = self.db.Rules.one({'default': True})
            #if default_rules is None:
            #    # first time!
            #    default_rules = self.db.Rules()
            #    default_rules.name = u"Default rules"
            #    default_rules.default = True
            #    default_rules.save()
            #rules_id = default_rules._id

        # Temporary "migration" hack
        # XXX This can be deleted once migration is complete
        while self.db.PlayPoints.find({'user.$id': user._id, 'rules': rules_id}).count()>1:
            for p in self.db.PlayPoints.find({'user.$id': user._id, 'rules': rules_id}):
                p.delete()
                break

        return self.db.PlayPoints.one({'user.$id': user._id, 'rules': rules_id})


@route('/')
class HomeHandler(BaseHandler):

    def get(self):
        # default settings
        options = self.get_base_options()
        user = options['user']
        options['count_published_questions'] = \
          self.db.Question.find({'state': 'PUBLISHED'}).count()

        accepted_questions_count = None
        if user:
            accepted_questions_count = 0
            for q in (self.db.Question.collection
                      .find({'state': ACCEPTED})):
                #if not self.db.Question
                if not (self.db.QuestionReview
                       .find({'question.$id': q['_id'],
                              'user.$id': user._id})
                       .count()):
                    accepted_questions_count += 1

        options['accepted_questions_count'] = accepted_questions_count

        past_plays = 0
        if user:
            past_plays = (self.db.Play
                  .find({'users.$id': user._id})
                  .count())
        options['past_plays'] = past_plays
        options['page_title'] = ("%s - %s" %
                                 (settings.PROJECT_TITLE,
                                  settings.TAG_LINE))
        self.render("home.html", **options)


@route('/settings/$', name='settings')
class SettingsHandler(BaseHandler):
    """Currently all this does is changing your name and email but it might
    change in the future.
    """

    NEWSLETTER_FREQUENCIES = (
      'daily',
      'weekly',
      'bi-weekly',
      'monthly',
      'quarterly',
    )

    @login_redirect
    def get(self):
        options = self.get_base_options()
        initial = dict(email=options['user'].email,
                       first_name=options['user'].first_name,
                       last_name=options['user'].last_name,
                       )
        newsletter_settings = self.get_newsletter_settings(options['user'])
        newsletter_frequency_options = None
        if newsletter_settings and newsletter_settings.last_send:
            initial['newsletter_frequency'] = newsletter_settings.frequency
            newsletter_frequency_options = self.NEWSLETTER_FREQUENCIES
        options['form'] = SettingsForm(
          newsletter_frequency_options=newsletter_frequency_options,
          **initial
        )
        options['page_title'] = "Settings"
        came_from = self.get_argument('came_from', None)
        if came_from:
            assert came_from.startswith('/')
            assert '://' not in came_from
        options['came_from'] = came_from
        options['must_verify_email'] = (
          self.get_argument('email', None) == 'must'
        )
        self.render("user/settings.html", **options)

    @login_redirect
    def post(self):
        email = self.get_argument('email', u'').strip()
        first_name = self.get_argument('first_name', u'').strip()
        last_name = self.get_argument('last_name', u'').strip()
        newsletter_frequency = self.get_argument('newsletter_frequency', None)
        if newsletter_frequency:
            assert newsletter_frequency in self.NEWSLETTER_FREQUENCIES

        if email and not valid_email(email):
            raise HTTPError(400, "Not a valid email address")

        user = self.get_current_user()

        if email:
            existing_user = self.find_user_by_email(email)
            if existing_user and existing_user != user:
                raise HTTPError(400, "Email address already used by someone else")

        _email_verification_sent = False
        if user.email != email and email:
            self.send_email_verification(user, email)
            _email_verification_sent = True

        user.email = email
        user.first_name = first_name
        user.last_name = last_name
        user.save()

        if newsletter_frequency:
            newsletter_settings = self.get_newsletter_settings(user)
            newsletter_settings.frequency = newsletter_frequency
            newsletter_settings.save()

        if _email_verification_sent:
            self.push_flash_message("Settings saved",
              "An email has been sent for you to verify your email address")
        else:
            self.push_flash_message("Settings saved",
              "Your changes have been successfully saved")

        url = self.get_argument('came_from', '/')
        assert url.startswith('/'), url
        if _email_verification_sent:
            p = '&' if '?' in url else '?'
            url += '%s=email-verification=sent' % p
        self.redirect(url)

    def send_email_verification(self, user, email):
        user_settings = self.get_user_settings(user)
        if not user_settings:
            user_settings = self.create_user_settings(user)
        add_date_ts = mktime(user.add_date.timetuple())
        tag = '%s-%s' % (email, add_date_ts)
        hash = md5(tag).hexdigest()

        url = '%s://%s' % (self.request.protocol, self.request.host)
        url += self.reverse_url('verify_email',
                               user._id,
                               hash)
        options = {
          'url': url,
          'user': user,
          'email': email,
        }
        body = self.render_string('user/verify-email.txt', **options)
        send_email(self.application.settings['email_backend'],
               "Kwissle email verification",
               body,
               self.application.settings['webmaster'],
               [email],
               )

@route('/verify-email/(\w{24})/([a-f0-9]+)/$', name='verify_email')
class VerifyEmailCallbackHandler(SettingsHandler):

    def get(self, _id, hash):
        try:
            user = self.db.User.one({'_id': ObjectId(_id)})
        except InvalidId:
            raise HTTPError(404, 'Invalid ID')
        if not user:
            raise HTTPError(404, 'User not found')

        # check the hash
        add_date_ts = mktime(user.add_date.timetuple())
        tag = '%s-%s' % (user.email, add_date_ts)
        if md5(tag).hexdigest() != hash:
            raise HTTPError(400, 'Invalid hash')

        user_settings = self.get_user_settings(user)
        user_settings.email_verified = user.email
        user_settings.save()

        self.push_flash_message("Email verified",
          "Awesome! Now your email address is verified")

        url = '/'
        self.redirect(url)

@route('/settings/social_media.json$', name='social_media_json')
class SocialMediaUserHandler(BaseHandler):

    def get(self):
        user_settings = self.get_current_user_settings()
        data = {}
        if user_settings:
            if user_settings.twitter:
                data['twitter'] = 1
            if user_settings.facebook:
                data['facebook'] = 1
        self.write_json(data)


class BaseAuthHandler(BaseHandler):

    def get_next_url(self, default='/'):
        next = default
        if self.get_argument('next', None):
            next = self.get_argument('next')
        elif self.get_cookie('next', None):
            next = self.get_cookie('next')
            self.clear_cookie('next')
        return next

    def notify_about_new_user(self, user, extra_message=None):
        #return # temporarily commented out
        if self.application.settings['debug']:
            return

        try:
            self._notify_about_new_user(user, extra_message=extra_message)
        except:
            # I hate to have to do this but I don't want to make STMP errors
            # stand in the way of getting signed up
            logging.error("Unable to notify about new user", exc_info=True)

    def _notify_about_new_user(self, user, extra_message=None):
        subject = "New user!"
        email_body = "%s %s\n" % (user.first_name, user.last_name)
        email_body += "%s\n" % user.email
        if extra_message:
            email_body += '%s\n' % extra_message

        send_email(self.application.settings['email_backend'],
                   subject,
                   email_body,
                   self.application.settings['webmaster'],
                   self.application.settings['admin_emails'],
                   )

    def make_username(self, first_name, last_name):
        def simple(s):
            return s.lower().replace(' ','').replace('-','')
        return '%s%s' % (simple(first_name), simple(last_name))

    def post_login_successful(self, user, previous_user=None):
        """executed by the Google, Twitter and Facebook authentication handlers"""
        if previous_user is None:
            if self.get_cookie('previous_user', None):
                previous_user_id = self.get_cookie('previous_user')
                previous_user = self.db.User.one({'_id': ObjectId(previous_user_id)})

        if previous_user:
            # change every PlayedQuestion
            for played_question in self.db.PlayedQuestion.find({'user.$id': previous_user._id}):
                played_question.user = user
                played_question.save()

            # change every PlayPoint done with the previous user
            previous_play_points = self.db.PlayPoints.one({'user.$id': user._id})
            for play_points in self.db.PlayPoints.find({'user.$id': previous_user._id}):
                play_points.user = user
                play_points.save()

                if previous_play_points:
                    previous_play_points.merge(play_points)


            for play in self.db.Play.find({'users.$id': previous_user._id}):
                play.users.remove(previous_user)
                play.users.append(user)
                play.save()

            for play in self.db.Play.find({'winner.$id': previous_user._id}):
                play.winner = user
                play.save()

            for msg in self.db.PlayMessage.find({'from.$id': previous_user._id}):
                msg['from'] = user
                msg.save()

            for msg in self.db.PlayMessage.find({'to.$id': previous_user._id}):
                msg.to = user
                msg.save()

            previous_user.delete()


@route('/login/', name='login')
class LoginHandler(BaseAuthHandler):

    def get(self):
        options = self.get_base_options()
        anonymous_play_points = None
        if options['user'] and options['user'].anonymous:
            play_points = (self.db.PlayPoints
                            .one({'user.$id': options['user']._id}))
            if play_points:
                anonymous_play_points = play_points.points
            self.set_cookie('previous_user', str(options['user']._id),
                             expires_days=1)
        options['anonymous_play_points'] = anonymous_play_points
        self.render("user/login.html", **options)


@route('/login/normal-registration/', name='login_normal_registration_interest')
class NormalRegistrationInterestHandler(LoginHandler):  # pragma: no cover
    def get(self):
        options = self.get_base_options()
        options['page_title'] = "Normal registration"
        http_user_agent = self.request.headers.get('User-Agent')
        logging.warn("Someone prefers a normal registration form (%s)"
                     % http_user_agent)
        self.render("user/normal-registration.html", **options)


@route('/login/fake/', name='fake_login')
class FakeLoginHandler(LoginHandler):  # pragma: no cover
    def get(self):
        assert self.application.settings['debug']
        if self.get_argument('username', None):
            user = self.find_user(self.get_argument('username'))
            self.set_secure_cookie("user", str(user._id), expires_days=100)
            return self.redirect(self.get_next_url())
        else:
            users = self.db.User.find()
            usernames = []
            for user in self.db.User.find().sort('username'):
                usernames.append(dict(username=user.username,
                                      email=user.email,
                                      questions=(self.db.Question
                                                 .find({'author.$id': user._id})
                                                 .count())))
            self.render("user/fake_login.html", users=usernames)


class CredentialsError(Exception):
    pass

@route('/auth/login/', name='auth_login')
class AuthLoginHandler(BaseAuthHandler): # pragma: no cover

    def check_credentials(self, username, password):
        logging.warn("Deprecated method")
        user = self.find_user(username)
        if not user:
            # The reason for this sleep is that if a hacker tries every single
            # brute-force email address he can think of he would be able to
            # get quick responses and test many passwords. Try to put some break
            # on that.
            sleep(0.5)
            raise CredentialsError("No user by that email address")

        if not user.check_password(password):
            raise CredentialsError("Incorrect password")

        return user


@route('/auth/login/browserid/', name='auth_login_browserid')
class BrowserIDAuthLoginHandler(AuthLoginHandler):

    def check_xsrf_cookie(self):
        pass

    @tornado.web.asynchronous
    def post(self):
        assertion = self.get_argument('assertion')
        http_client = tornado.httpclient.AsyncHTTPClient()
        domain = self.request.host
        url = 'https://browserid.org/verify'
        data = {
          'assertion': assertion,
          'audience': domain,
        }
        response = http_client.fetch(
          url,
          method='POST',
          body=urlencode(data),
          callback=self.async_callback(self._on_response)
        )

    def _on_response(self, response):
        if 'email' in response.body:
            # all is well
            struct = tornado.escape.json_decode(response.body)
            assert struct['email']
            email = struct['email']
            user = self.db.User.find_by_email(email)

            if user:
                next_url = self.get_next_url()
            else:
                username = email.split('@')[0]
                c = 1
                while self.db.User.find_by_username(username):
                    # taken!
                    c += 1
                    username = email.split('@')[0] + '-%d' % c
                # create a new account
                user = self.db.User()
                user.username = unicode(username)
                user.email = unicode(email)
                user.set_password(random_string(20))
                user.save()
                next_url = self.reverse_url('settings')

            self.post_login_successful(user)
            self.set_secure_cookie('user', str(user._id),
                                   expires_days=100)
            self.write_json({'next_url': next_url})

        else:
            self.write_json({'ERROR': response.body})
        self.finish()


@route('/auth/google/', name='auth_google')
class GoogleAuthHandler(BaseAuthHandler, tornado.auth.GoogleMixin):
    @tornado.web.asynchronous
    def get(self):
        if self.get_argument("openid.mode", None):
            self.get_authenticated_user(self.async_callback(self._on_auth))
            return
        if self.get_argument('next', None):
            # because this is going to get lost when we get back from Google
            # stick it in a cookie
            self.set_cookie('next', self.get_argument('next'))
        self.authenticate_redirect()

    def _on_auth(self, user):
        if not user:
            raise HTTPError(500, "Google auth failed")
        if not user.get('email'):
            raise HTTPError(500, "No email provided")

        user_struct = user
        locale = user.get('locale') # not sure what to do with this yet
        first_name = user.get('first_name')
        last_name = user.get('last_name')
        username = user.get('username')
        email = user['email']
        if not username:
            username = email.split('@')[0]

        user = self.db.User.one(dict(username=username))
        if not user:
            user = self.db.User.one(dict(email=email))
            if user is None:
                user = self.db.User.one(dict(email=re.compile(re.escape(email), re.I)))

        if not user:
            # create a new account
            user = self.db.User()
            user.username = username
            user.email = email
            if first_name:
                user.first_name = first_name
            if last_name:
                user.last_name = last_name
            user.set_password(random_string(20))
            user.save()

            self.notify_about_new_user(user, extra_message="Used Google OpenID")

        user_settings = self.get_user_settings(user)
        if not user_settings:
            user_settings = self.create_user_settings(user)
        user_settings.google = user_struct
        if user.email:
            user_settings.email_verified = user.email
        user_settings.save()

        self.post_login_successful(user)
        self.set_secure_cookie("user", str(user._id), expires_days=100)
        self.redirect(self.get_next_url())


@route('/auth/facebook/', name='auth_facebook')
class FacebookAuthHandler(BaseAuthHandler, tornado.auth.FacebookMixin):

    @tornado.web.asynchronous
    def get(self):
        if self.get_argument("session", None):
            self.get_authenticated_user(self.async_callback(self._on_auth))
            return
        self.authenticate_redirect()

    def _on_auth(self, user_struct):
        if not user_struct:
            raise HTTPError(500, "Facebook auth failed")
        logging.info(user_struct)
        # Example response:
        #  {'username': u'peterbecom',
        #   'pic_square': u'http://profile.ak.fbcdn.net/hprofile-ak-snc4/174129_564710728_3557794_q.jpg',
        #   'first_name': u'Peter',
        #   'last_name': u'Bengtsson',
        #   'name': u'Peter Bengtsson',
        #   'locale': u'en_GB',
        #   'session_expires': 1303218000,
        #   'session_key': u'2.UYZ9b8YQuRMjdcFy0RtAbg__.3600.1303218000.0-564710728',
        #   'profile_url': u'http://www.facebook.com/peterbecom',
        #   'uid': 564710728}
        user = None
        username = user_struct.get('username')
        email = user_struct.get('email')
        first_name = user_struct.get('first_name')
        last_name = user_struct.get('last_name')
        if not username:
            username = self.make_username(first_name, last_name)

        user = self.find_user(username)
        if not user:
            if email:
                user = self.find_user_by_email(email)

        if not user:
            new = True
            user = self.db.User()
            user.username = username
            user.email = email
            if first_name:
                user.first_name = first_name
            if last_name:
                user.last_name = last_name
            user.set_password(random_string(20))
        else:
            new = False
            if first_name:
                user.first_name = first_name
            if last_name:
                user.last_name = last_name
        user.save()

        if new:
            self.push_flash_message("Welcome!",
                                    "You username is %s" % user.username)
            self.notify_about_new_user(user,
                                       extra_message="Used Facebook to sign in")

        user_settings = self.get_user_settings(user)
        if not user_settings:
            user_settings = self.create_user_settings(user)
        user_settings.facebook = user_struct
        if email:
            user_settings.email_verified = email
        user_settings.save()

        self.post_login_successful(user)
        # XXX: expires_days needs to reflect user_struct['session_expires']
        self.set_secure_cookie("user", str(user._id), expires_days=100)
        if new:
            self.redirect(self.reverse_url('settings'))
        else:
            self.redirect(self.get_next_url())

@route('/auth/twitter/', name='auth_twitter')
class TwitterAuthHandler(BaseAuthHandler, tornado.auth.TwitterMixin):
    @tornado.web.asynchronous
    def get(self):
        if self.get_argument("oauth_token", None):
            self.get_authenticated_user(self.async_callback(self._on_auth))
            return
        self.authenticate_redirect()

    def _on_auth(self, user_struct):
        if not user_struct:
            raise HTTPError(500, "Twitter auth failed")
        #from pprint import pprint
        #pprint(user_struct)
        #if not user_struct.get('email'):
        #    raise HTTPError(500, "No email provided")
        username = user_struct.get('username')
        #locale = user_struct.get('locale') # not sure what to do with this yet
        first_name = user_struct.get('first_name', user_struct.get('name'))
        last_name = user_struct.get('last_name')
        email = user_struct.get('email')
        #access_token = user_struct['access_token']['key']
        #profile_image_url = user_struct.get('profile_image_url', None)

        user = self.find_user(username)

        if not user:
            # create a new account
            user = self.db.User()
            user.username = username
            user.email = email
            if first_name:
                user.first_name = first_name
            if last_name:
                user.last_name = last_name
            user.set_password(random_string(20))
            user.save()
            self.push_flash_message("Welcome!", "You username is %s" % user.username)
            self.notify_about_new_user(user, extra_message="Used Twitter")
        else:
            if first_name:
                user.first_name = first_name
            if last_name:
                user.last_name = last_name
            user.save()
            self.push_flash_message("Logged in", "You username is %s" % user.username)

        user_settings = self.get_user_settings(user)
        if not user_settings:
            user_settings = self.create_user_settings(user)
        user_settings.twitter = user_struct
        if email:
            user_settings.email_verified = email
        user_settings.save()

        self.post_login_successful(user)
        self.set_secure_cookie("user", str(user._id), expires_days=100)
        self.redirect(self.get_next_url())


@route(r'/auth/logout/', name='logout')
class AuthLogoutHandler(BaseAuthHandler):
    def get(self):
        self.clear_all_cookies()
        self.redirect(self.get_next_url())


@route(r'/help/([\w-]*)', name='help')
class HelpHandler(BaseHandler):

    SEE_ALSO = (
      ['/', u"Help"],
      u"About",
      ['/a-good-question', u"Writing a good question"],
      ['/rules', u"Rules"],
      ['/question-workflow', u"Question workflow"],
      ['/browsers', u"Browsers"],
      #u"News",
      #['/API', u"Developers' API"],
      #u"Bookmarklet",
      #['/Google-calendar', u"Google Calendar"],
      #u"Feature requests",
      #['/Secure-passwords', u"Secure passwords"],
      #['/Internet-Explorer', u"Internet Explorer"],
    )

    def get(self, page):
        options = self.get_base_options()
        self.application.settings['template_path']
        if page == '':
            page = 'index'

        filename = "help/%s.html" % page.lower()
        if os.path.isfile(os.path.join(self.application.settings['template_path'],
                                       filename)):
            if page.lower() == 'api':
                raise NotImplementedError
                self._extend_api_options(options)
            elif page.lower() == 'bookmarklet':
                raise NotImplementedError
                self._extend_bookmarklet_options(options)
            elif page == 'index':
                self._extend_index_options(options)

            return self.render(filename, **options)

        raise HTTPError(404, "Unknown page")

    def get_see_also_links(self, exclude_index=False):
        for each in self.SEE_ALSO:
            if isinstance(each, basestring):
                link = '/%s' % each.replace(' ','-')
                label = each
            else:
                link, label = each
            if exclude_index and '/help' + link == self.request.path:
                continue
            yield dict(link=link, label=label)

    def _extend_index_options(self, options):
        options['see_also_links'] = self.get_see_also_links(exclude_index=True)


@route('/settings/toggle/$', name='user_settings_toggle')
class UserSettingsToggle(BaseHandler):

    def check_xsrf_cookie(self):
        pass

    @tornado.web.authenticated
    def post(self):
        user_settings = self.get_current_user_settings(create_if_necessary=True)
        sound = self.get_argument('sound', None)
        _save = False
        if sound is not None:
            user_settings.disable_sound = not user_settings.disable_sound
            _save = True
        if _save:
            user_settings.save()
        else:
            raise HTTPError(400, "No valid settings toggled")
        self.write("OK")

@route('/socialmedia/$', name='social_media')
class SocialMediaHandler(BaseHandler):

    def get(self):
        options = self.get_base_options()
        options['page_title'] = "Social Media"
        self.render('social_media.html', **options)

@route('/socialmedia/facebook/$', name='social_media_facebook')
class SocialMediaFacebookHandler(BaseHandler):

    def get(self):
        options = self.get_base_options()
        options['page_title'] = "Facebook"
        self.render('social_media_facebook.html', **options)

@route('/socialmedia/twitter/$', name='social_media_twitter')
class SocialMediaTwitterHandler(BaseHandler):

    def get(self):
        options = self.get_base_options()
        options['page_title'] = "Twitter"
        self.render('social_media_twitter.html', **options)


@route('/sitemap.xml$', name='sitemap_xml')
class SitemapXMLHandler(BaseHandler):

    def get(self):
        self.set_header("Content-Type", "application/xml")
        global _CACHED_SITEMAP_DATA
        try:
            output, timestamp = _CACHED_SITEMAP_DATA
            if timestamp > time():
                self.write(output)
                return
        except TypeError:
            pass

        # This limit is defined by Google. See the index documentation at
        # http://sitemaps.org/protocol.php#index
        limit = 50000
        sites = self.get_sites(limit)
        base_url = 'http://%s' % self.request.host

        output = self._get_output(sites, base_url)
        _CACHED_SITEMAP_DATA = (output, time() + 60 * 60)
        self.write(output)

    def _get_output(self, sites, base_url):
        top = etree.Element('urlset')
        top.set('xmlns', 'http://www.sitemaps.org/schemas/sitemap/0.9')
        #top.set('xmlns:image', 'http://www.sitemaps.org/schemas/sitemap-image/1.1')
        top.set('xmlns:image', 'http://www.google.com/schemas/sitemap-image/1.1')
        for site in sites:
            url = etree.SubElement(top, 'url')
            loc = etree.SubElement(url, 'loc')
            loc.text = '%s%s' % (base_url, site.location)
            if site.image:
                image = etree.SubElement(url, 'image:image')
                image_loc = etree.SubElement(image, 'image:loc')
                if site.image.startswith('http'):
                    image_loc.text = site.image
                else:
                    image_loc.text = '%s%s' % (base_url, site.image)

        output = '<?xml version="1.0" encoding="UTF-8"?>\n' + etree.tostring(top)
        return output

    def get_sites(self, limit):
        yield Site('/', datetime.date.today(), 'daily')
        url = self.reverse_url
        latest_date = datetime.date.today()
        for play_point in (self.db.PlayPoints.collection
                          .find().sort('modify_date', -1)
                          .limit(1)):
            latest_date = play_point['modify_date']
        yield Site(url('play_highscore'), latest_date, 'hourly')
        yield Site(url('stats_numbers'), changefreq='weekly')
        yield Site(url('stats_times_played'), changefreq='weekly')
        # help pages
        for see_also in HelpHandler.SEE_ALSO:
            try:
                url, __ = see_also
            except ValueError:
                url = '/%s' % see_also
            url = '/help' + url
            yield Site(url, changefreq='monthly')

        question_ids_with_images = [x['question'].id for x in
                                    self.db.QuestionImage.collection.find()]
        for question in self.db.Question.collection.find({'state': PUBLISHED}).sort('publish_date', -1).limit(limit - 10):
            image = None
            if question['_id'] in question_ids_with_images:
                image = (self.db.QuestionImage.collection
                       .one({'question.$id': question['_id']})
                       ['render_attributes']['src'])
            yield Site(get_question_slug_url(question),
                       question['publish_date'],
                       'monthly',
                       image=image)


_CACHED_SITEMAP_DATA = None

class Site:
    __slots__ = ('location', 'lastmod', 'changefreq', 'priority', 'image')
    def __init__(self, location, lastmod=None, changefreq=None,
                 priority=None, image=None):
        self.location = location
        self.lastmod = lastmod
        self.changefreq = changefreq
        self.priority = priority
        self.image = image


# this handler gets automatically appended last to all handlers inside app.py
class PageNotFoundHandler(BaseHandler):

    def get(self):
        path = self.request.path
        if not path.endswith('/'):
            new_url = '%s/' % path
            if self.request.query:
                new_url += '?%s' % self.request.query
            self.redirect(new_url)
            return
        self.send_page_not_found()
