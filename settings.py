PROJECT_TITLE = u"Kwissle"
APPS = (
  'main',
  'questions',
  'play',
  'chat',
)
DATABASE_NAME = "gkc"

LOGIN_URL = "/auth/login/"
NODE_URL = "http://%(host)s:8888/start"
NODE_DOMAIN = 'kwissle.com'

COOKIE_SECRET = "12orTzK2XQAGUYdkL5gmueJIFuY37EQn92XsTo1v/Vo="

#WEBMASTER = 'webmaster@kwissle.com'
WEBMASTER = 'mailer@elasticemail.com'
ADMIN_EMAILS = ['peterbe@gmail.com', 'ashleynoval@gmail.com']

TWITTER_CONSUMER_KEY = 'UcZ80RJk7x4FVWE0d93ig'
TWITTER_CONSUMER_SECRET = open('twitter_consumer_secret').read().strip()

FACEBOOK_API_KEY = '0bdf577fe3dc898fc740a3999a1f1ce0'
FACEBOOK_SECRET = open('facebook_consumer_secret').read().strip()

try:
    from local_settings import *
except ImportError:
    pass
