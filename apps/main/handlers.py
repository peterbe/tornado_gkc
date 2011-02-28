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

# app
from utils.routes import route, route_redirect
from models import *
from utils.send_mail import send_email
from utils.decorators import login_required
from utils import parse_datetime, niceboolean, \
  DatetimeParseError, valid_email, random_string, \
  all_hash_tags, all_atsign_tags, generate_random_color
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
        if not isinstance(exception, tornado.web.HTTPError) and \
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

        send_email(self.application.settings['email_backend'],
                   subject,
                   out.getvalue(),
                   self.application.settings['webmaster'],
                   self.application.settings['admin_emails'],
                   )

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
                       is_admin_user=False)

        # default settings
        settings = dict(
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
            if user_settings:
                settings['disable_sound'] = user_settings.disable_sound

        options['settings'] = settings

        options['git_revision'] = self.application.settings['git_revision']
        options['debug'] = self.application.settings['debug']

        return options


@route('/')
class HomeHandler(BaseHandler):

    def get(self):
        # default settings
        options = self.get_base_options()
        user = options['user']
        self.render("home.html", **options)


@route('/user/settings(\.js|/)$')
class UserSettingsHandler(BaseHandler):
    def get(self, format=None):
        # default initials
        default = dict()
        setting_keys = list()

        for key in UserSettings.get_bool_keys():
            default[key] = False
            setting_keys.append(key)
        default['first_hour'] = 8

        user = self.get_current_user()
        if user:
            user_settings = self.get_current_user_settings(user)
            if user_settings:
                for key in setting_keys:
                    default[key] = getattr(user_settings, key, False)
                default['first_hour'] = getattr(user_settings, 'first_hour', 8)
            else:
                user_settings = self.db.UserSettings()
                user_settings.user = user
                user_settings.save()

        if format == '.js':
            self.set_header("Content-Type", "text/javascript; charset=UTF-8")
            self.set_header("Cache-Control", "public,max-age=0")
            self.write('var SETTINGS=%s;' % tornado.escape.json_encode(default))
        else:
            self.render("user/settings.html", **dict(default, user=user))

    def post(self, format=None):
        user = self.get_current_user()
        if not user:
            raise tornado.web.HTTPError(403, "Not logged in yet")
            #user = self.db.User()
            #user.save()
            #self.set_secure_cookie("user", str(user.guid), expires_days=100)

        user_settings = self.get_current_user_settings(user)
        if user_settings:
            hide_weekend = user_settings.hide_weekend
            monday_first = user_settings.monday_first
            disable_sound = user_settings.disable_sound
            offline_mode = getattr(user_settings, 'offline_mode', False)
        else:
            user_settings = self.db.UserSettings()
            user_settings.user = user
            user_settings.save()

        for key in ('monday_first', 'hide_weekend', 'disable_sound',
                    'offline_mode', 'ampm_format'):
            user_settings[key] = bool(self.get_argument(key, None))

        if self.get_argument('first_hour', None) is not None:
            first_hour = int(self.get_argument('first_hour'))
            user_settings['first_hour'] = first_hour

        user_settings.save()
        url = "/"
        if self.get_argument('anchor', None):
            if self.get_argument('anchor').startswith('#'):
                url += self.get_argument('anchor')
            else:
                url += '#%s' % self.get_argument('anchor')

        self.redirect(url)


@route('/user/$')
class AccountHandler(BaseHandler):
    def get(self):
        user_id = self.get_secure_cookie('user')
        if user_id:
            user = self.db.User.one(dict(_id=ObjectId(user_id)))
            if not user:
                return self.write("Error. User does not exist")
            options = dict(
              email=user.email,
              first_name=user.first_name,
              last_name=user.last_name,
            )

            self.render("user/change-account.html", **options)
        else:
            self.render("user/account.html")

    @login_required
    def post(self):
        username = self.get_argument('username').strip()
        email = self.get_argument('email', u"").strip()
        first_name = self.get_argument('first_name', u"").strip()
        last_name = self.get_argument('last_name', u"").strip()

        if not username:
            raise tornado.web.HTTPError(400, "Username invalid")

        if email and not valid_email(email):
            raise tornado.web.HTTPError(400, "Not a valid email address")

        user = self.get_current_user()

        existing_user = self.find_user(username)
        if existing_user and existing_user != user:
            raise tornado.web.HTTPError(400, "Username already used by someone else")

        if email:
            existing_user = self.find_user_by_email(email)
            if existing_user and existing_user != user:
                raise tornado.web.HTTPError(400, "Email address already used by someone else")

        user.username = username
        user.email = email
        user.first_name = first_name
        user.last_name = last_name
        user.save()

        self.redirect('/')

hex_to_int = lambda s: int(s, 16)
int_to_hex = lambda i: hex(i).replace('0x', '')

@route('/user/forgotten/$')
class ForgottenPasswordHandler(BaseHandler):

    def get(self, error=None, success=None):
        options = self.get_base_options()
        options['error'] = error and error or \
          self.get_argument('error', None)
        options['success'] = success and success or \
          self.get_argument('success', None)
        self.render("user/forgotten.html", **options)

    #@tornado.web.asynchronous
    def post(self):
        email = self.get_argument('email')
        if not valid_email(email):
            raise tornado.web.HTTPError(400, "Not a valid email address")

        existing_user = self.find_user_by_email(email)
        if not existing_user:
            self.get(error="%s is a valid email address but no account exists matching this" % \
              email)
            return

        from tornado.template import Loader
        loader = Loader(self.application.settings['template_path'])

        recover_url = self.lost_url_for_user(existing_user._id)
        recover_url = self.request.full_url() + recover_url
        email_body = loader.load('user/reset_password.txt')\
          .generate(recover_url=recover_url,
                    first_name=existing_user.first_name,
                    signature=self.application.settings['title'])

        #if not isinstance(email_body, unicode):
        #    email_body = unicode(email_body, 'utf-8')

        if 1:#try:
            assert send_email(self.application.settings['email_backend'],
                      "Password reset for on %s" % self.application.settings['title'],
                      email_body,
                      self.application.settings['webmaster'],
                      [existing_user.email])

            self.redirect('/user/forgotten/?success=%s' %
              quote("Password reset instructions sent to %s" % \
              existing_user.email)
            )
            #self.get(success="Password reset instructions sent to %s" % \
            #  existing_user.email)
        #finally:

        #self.finish()


    ORIGIN_DATE = datetime.date(2000, 1, 1)

    def lost_url_for_user(self, user_id):
        days = int_to_hex((datetime.date.today() - self.ORIGIN_DATE).days)
        secret_key = self.application.settings['cookie_secret']
        hash = md5(secret_key + days + str(user_id)).hexdigest()
        return 'recover/%s/%s/%s/'%\
                       (user_id, days, hash)

    def hash_is_valid(self, user_id, days, hash):
        secret_key = self.application.settings['cookie_secret']
        if md5(secret_key + days + str(user_id)).hexdigest() != hash:
            return False # Hash failed
        # Ensure days is within a week of today
        days_now = (datetime.date.today() - self.ORIGIN_DATE).days
        days_old = days_now - hex_to_int(days)
        return days_old < 7


@route('/user/forgotten/recover/(\w+)/([a-f0-9]+)/([a-f0-9]{32})/$')
class RecoverForgottenPasswordHandler(ForgottenPasswordHandler):
    def get(self, user_id, days, hash, error=None):
        if not self.hash_is_valid(user_id, days, hash):
            return self.write("Error. Invalid link. Expired probably")
        user = self.db.User.one({'_id': ObjectId(user_id)})
        if not user:
            return self.write("Error. Invalid user")

        options = self.get_base_options()
        options['error'] = error
        self.render("user/recover_forgotten.html", **options)

    def post(self, user_id, days, hash):
        if not self.hash_is_valid(user_id, days, hash):
            raise tornado.web.HTTPError(400, "invalid hash")

        new_password = self.get_argument('password')
        if len(new_password) < 4:
            raise tornado.web.HTTPError(400, "password too short")

        user = self.db.User.one({'_id': ObjectId(user_id)})
        if not user:
            raise tornado.web.HTTPError(400, "invalid hash")

        user.set_password(new_password)
        user.save()

        self.set_secure_cookie("user", str(user._id), expires_days=100)

        self.redirect("/")


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
        email_body += "%s events\n" % \
          self.db.Event.find({'user.$id': user._id}).count()
        if extra_message:
            email_body += '%s\n' % extra_message
        user_settings = self.get_current_user_settings(user)
        if user_settings:
            bits = []
            for key, value in UserSettings.structure.items():
                if value == bool:
                    yes_or_no = getattr(user_settings, key, False)
                    bits.append('%s: %s' % (key, yes_or_no and 'Yes' or 'No'))
            email_body += "User settings:\n\t%s\n" % ', '.join(bits)

        send_email(self.application.settings['email_backend'],
                   subject,
                   email_body,
                   self.application.settings['webmaster'],
                   self.application.settings['admin_emails'])



@route('/user/signup/')
class SignupHandler(BaseAuthHandler):

    def get(self):
        if self.get_argument('validate_username', None):
            username = self.get_argument('validate_username').strip()
            if self.has_user(username):
                result = dict(error='taken')
            else:
                result = dict(ok=True)
            self.write_json(result)
        else:
            raise tornado.web.HTTPError(404, "Nothing to check")

    def post(self):
        username = self.get_argument('username', u'').strip()
        email = self.get_argument('email', u'').strip()
        password = self.get_argument('password')
        first_name = self.get_argument('first_name', u'').strip()
        last_name = self.get_argument('last_name', u'').strip()

        if not username:
            return self.write("Error. No username provided")
        if email and not valid_email(email):
            raise tornado.web.HTTPError(400, "Not a valid email address")
        if not password:
            return self.write("Error. No password provided")

        if self.has_user(email):
            return self.write("Error. Email already taken")

        if len(password) < 4:
            return self.write("Error. Password too short")

        user = self.get_current_user()
        if not user:
            user = self.db.User()
        user.username = username
        user.email = email
        user.set_password(password)
        user.first_name = first_name
        user.last_name = last_name
        user.save()

        self.notify_about_new_user(user)

        self.set_secure_cookie("user", str(user._id), expires_days=100)

        self.redirect('/')



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
            raise tornado.web.HTTPError(500, "Google auth failed")
        if not user.get('email'):
            raise tornado.web.HTTPError(500, "No email provided")
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
            raise tornado.web.HTTPError(500, "Twitter auth failed")
        from pprint import pprint
        pprint(user)
        #if not user.get('email'):
        #    raise tornado.web.HTTPError(500, "No email provided")
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

            self.notify_about_new_user(user, extra_message="Used Twitter")
        else:
            if first_name:
                user.first_name = first_name
            if last_name:
                user.last_name = last_name
            user.save()

        user_settings = self.get_user_settings(user)
        if not user_settings:
            user_settings = self.create_user_settings(user)
        user_settings['twitter_access_token'] = unicode(access_token)
        if profile_image_url:
            user_settings['twitter_profile_image_url'] = unicode(profile_image_url)
        user_settings.save()

        self.set_secure_cookie("user", str(user._id), expires_days=100)
        self.redirect(self.get_next_url())


@route(r'/auth/logout/')
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

        raise tornado.web.HTTPError(404, "Unknown page")

    def get_see_also_links(self):
        for each in self.SEE_ALSO:
            if isinstance(each, basestring):
                link = '/%s' % each.replace(' ','-')
                label = each
            else:
                link, label = each
            yield dict(link=link, label=label)
