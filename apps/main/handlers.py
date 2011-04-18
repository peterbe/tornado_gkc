# python
import traceback
import httplib
from hashlib import md5
from cStringIO import StringIO
from urlparse import urlparse
from pprint import pprint
from collections import defaultdict
from pymongo.objectid import InvalidId, ObjectId
from time import mktime, sleep
import datetime
from urllib import quote
import os.path
import re
import logging

# tornado
import tornado.auth
import tornado.web
from tornado.web import HTTPError

# app
from utils.routes import route, route_redirect
from models import *
from utils.send_mail import send_email
from utils.decorators import login_required, login_redirect
from utils import parse_datetime, niceboolean, \
  DatetimeParseError, valid_email, random_string, \
  all_hash_tags, all_atsign_tags, generate_random_color
from forms import SettingsForm
import settings


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
    def _handle_request_exception(self, exception):
        if not isinstance(exception, HTTPError) and \
          not self.application.settings['debug']:
            # ie. a 500 error
            try:
                self._email_exception(exception)
            except:
                print "** Failing even to email exception **"

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
                   self.application.settings['admin_emails'],
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

    # shortcut where the user parameter is not optional
    def get_user_settings(self, user, fast=False):
        return self.get_current_user_settings(user=user, fast=fast)

    def get_current_user_settings(self, user=None, fast=False):
        if user is None:
            user = self.get_current_user()

        if not user:
            raise ValueError("Can't get settings when there is no user")
        _search = {'user.$id': user['_id']}
        if fast:
            return self.db[UserSettings.__collection__].one(_search) # skip mongokit
        else:
            return self.db.UserSettings.one(_search)

    def create_user_settings(self, user, **default_settings):
        user_settings = self.db.UserSettings()
        user_settings.user = user
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
                       total_battle_points=0,
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
                    user_name = "stranger"
                options['user_name'] = user_name

            # override possible settings
            user_settings = self.get_current_user_settings(user)
            #options['total_question_points'] = \
            #  self.get_total_question_points(user)
            options['total_battle_points'] = \
              self.get_total_battle_points(user)

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
        for msg in self.db.FlashMessage.collection.find({'user.$id':user._id})\
          .sort('add_date', -1).limit(1):
            if msg['title'] == title and msg['text'] == text:
                # but was it several seconds ago?
                if (datetime.datetime.now() - msg['add_date']).seconds < 3:
                    return
        msg = self.db.FlashMessage()
        msg.user = user
        msg.title = unicode(title)
        msg.text = unicode(text)
        msg.save()

    def pull_flash_messages(self, unread=True, user=None):
        if user is None:
            user = self.get_current_user()
            if not user:
                return []
        _search = {'user.$id':user._id}
        if unread:
            _search['read'] = False
        return self.db.FlashMessage.find(_search).sort('add_date', 1)


    def get_total_battle_points(self, user):
        return 0



@route('/')
class HomeHandler(BaseHandler):

    def get(self):
        # default settings
        options = self.get_base_options()
        user = options['user']
        options['count_published_questions'] = \
          self.db.Question.find({'state': 'PUBLISHED'}).count()
        self.render("home.html", **options)


route_redirect('/settings$', '/settings/', name='settings_shortcut')
@route('/settings/$', name='settings')
class SettingsHandler(BaseHandler):
    """Currently all this does is changing your name and email but it might
    change in the future.
    """
    @login_redirect
    def get(self):
        options = self.get_base_options()
        initial = dict(email=options['user'].email,
                       first_name=options['user'].first_name,
                       last_name=options['user'].last_name,
                       )
        options['form'] = SettingsForm(**initial)
        options['page_title'] = "Settings"
        self.render("user/settings.html", **options)

    @login_redirect
    def post(self):
        email = self.get_argument('email', u'').strip()
        first_name = self.get_argument('first_name', u'').strip()
        last_name = self.get_argument('last_name', u'').strip()

        if email and not valid_email(email):
            raise HTTPError(400, "Not a valid email address")

        user = self.get_current_user()

        if email:
            existing_user = self.find_user_by_email(email)
            if existing_user and existing_user != user:
                raise HTTPError(400, "Email address already used by someone else")

        user.email = email
        user.first_name = first_name
        user.last_name = last_name
        user.save()

        self.push_flash_message("Settings saved",
          "Your changes have been successfully saved")
        self.redirect('/')

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

        #user_settings = self.get_current_user_settings(user)
        #if user_settings:
        #    bits = []
        #    for key, value in UserSettings.structure.items():
        #        if value == bool:
        #            yes_or_no = getattr(user_settings, key, False)
        #            bits.append('%s: %s' % (key, yes_or_no and 'Yes' or 'No'))
        #    email_body += "User settings:\n\t%s\n" % ', '.join(bits)

        send_email(self.application.settings['email_backend'],
                   subject,
                   email_body,
                   self.application.settings['webmaster'],
                   self.application.settings['admin_emails'],
                   )

route_redirect('/login', '/login/', name='login_shortcut')
@route('/login/', name='login')
class LoginHandler(BaseAuthHandler):

    def get(self):
        options = self.get_base_options()
        self.render("user/login.html", **options)


@route('/login/fake/', name='fake_login')
class FakeLoginHandler(LoginHandler):
    def get(self):
        assert self.application.settings['debug']
        if self.get_argument('username', None):
            user = self.find_user(self.get_argument('username'))
            self.set_secure_cookie("user", str(user._id), expires_days=100)
            return self.redirect(self.get_next_url())
        else:
            users = self.db.User.find()
            self.render("user/fake_login.html", users=users)


class CredentialsError(Exception):
    pass

@route('/auth/login/')
class AuthLoginHandler(BaseAuthHandler):

    def check_credentials(self, username, password):
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


    def post(self):
        username = self.get_argument('username')
        password = self.get_argument('password')
        try:
            user = self.check_credentials(username, password)
        except CredentialsError, msg:
            return self.write("Error: %s" % msg)

        #self.set_secure_cookie("guid", str(user.guid), expires_days=100)
        self.set_secure_cookie("user", str(user._id), expires_days=100)

        self.redirect(self.get_next_url())
        #if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
        #    return str(user.guid)
        #else:
        #    self.redirect(self.get_next_url())


@route('/auth/google/')
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
        locale = user.get('locale') # not sure what to do with this yet
        first_name = user.get('first_name')
        last_name = user.get('last_name')
        username = user.get('username')
        email = user['email']
        if not username:
            username = email.split('@')[0]

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

        self.set_secure_cookie("user", str(user._id), expires_days=100)

        self.redirect(self.get_next_url())


@route('/auth/twitter/')
class TwitterAuthHandler(BaseAuthHandler, tornado.auth.TwitterMixin):
    @tornado.web.asynchronous
    def get(self):
        if self.get_argument("oauth_token", None):
            self.get_authenticated_user(self.async_callback(self._on_auth))
            return
        self.authenticate_redirect()

    def _on_auth(self, user):
        if not user:
            raise HTTPError(500, "Twitter auth failed")
        from pprint import pprint
        pprint(user)
        #if not user.get('email'):
        #    raise HTTPError(500, "No email provided")
        username = user.get('username')
        #locale = user.get('locale') # not sure what to do with this yet
        first_name = user.get('first_name', user.get('name'))
        last_name = user.get('last_name')
        email = user.get('email')
        access_token = user['access_token']['key']
        profile_image_url = user.get('profile_image_url', None)

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
        user_settings['twitter_access_token'] = unicode(access_token)
        if profile_image_url:
            user_settings['twitter_profile_image_url'] = unicode(profile_image_url)
        user_settings.save()

        self.set_secure_cookie("user", str(user._id), expires_days=100)
        self.redirect(self.get_next_url())


@route(r'/auth/logout/', name='logout')
class AuthLogoutHandler(BaseAuthHandler):
    def get(self):
        self.clear_all_cookies()
        self.redirect(self.get_next_url())


@route(r'/help/([\w-]*)')
class HelpHandler(BaseHandler):

    SEE_ALSO = (
      ['/', u"Help"],
      u"About",
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
                self._extend_api_options(options)
            elif page.lower() == 'bookmarklet':
                self._extend_bookmarklet_options(options)

            return self.render(filename, **options)

        raise HTTPError(404, "Unknown page")

    def get_see_also_links(self):
        for each in self.SEE_ALSO:
            if isinstance(each, basestring):
                link = '/%s' % each.replace(' ','-')
                label = each
            else:
                link, label = each
            yield dict(link=link, label=label)
