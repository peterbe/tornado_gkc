import os.path as op
ROOT = op.abspath(op.dirname(__file__))
path = lambda *a: op.join(ROOT, *a)

PROJECT_TITLE = u"Kwissle"
TAG_LINE = "a real-time general knowledge quiz battle game"
APPS = (
  'main',
  'questions',
  'play',
  'chat',
  'stats',
)
DATABASE_NAME = "gkc"

LOGIN_URL = "/auth/login/"
#NODE_URL = "http://%(host)s:8888/start"
#NODE_DOMAIN = 'kwissle.com'

COMPUTER_USERNAME = u'Computer'
COOKIE_SECRET = "12orTzK2XQAGUYdkL5gmueJIFuY37EQn92XsTo1v/Vo="

WEBMASTER = 'webmaster@kwissle.com'
#WEBMASTER = 'mailer@elasticemail.com'
ADMIN_EMAILS = ['peterbe@gmail.com', 'ashleynoval@gmail.com']
DEVELOPER_EMAILS = ['peterbe@gmail.com']

TWITTER_CONSUMER_KEY = 'UcZ80RJk7x4FVWE0d93ig'
TWITTER_CONSUMER_SECRET = open(path('twitter_consumer_secret')).read().strip()

FACEBOOK_API_KEY = '0bdf577fe3dc898fc740a3999a1f1ce0'
FACEBOOK_SECRET = open(path('facebook_consumer_secret')).read().strip()

XAPIAN_LOCATION = path('xapian_db')

THUMBNAIL_DIRECTORY = path('static/thumbnails')

try:
    from local_settings import *
except ImportError:
    pass
