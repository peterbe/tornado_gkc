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
  'widget',
  'twitter',
  'rules',
)
DATABASE_NAME = "gkc"

LOGIN_URL = "/login/"
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

# used for the twitter app that has write access
TWITTER_POSTINGS_CONSUMER_KEY = 'KTydZWQ6Ocl6Ov8BlMb9w'
TWITTER_POSTINGS_CONSUMER_SECRET = open(path('twitter_postings_consumer_secret')).read().strip()
TWITTER_KWISSLE_ACCESS_TOKENS = (
  {'key': '310217734-Jo3Xh0SYerZccLz5s38o34jeWjBBwyga7l0tfwxg',
   'screen_name': 'kwissle',
   'secret': '02xXfro69vKoKGEeKUpmJnh50pn5Bc0ebVZskCOwmuQ',
   'user_id': '310217734'},
)

FACEBOOK_API_KEY = '0bdf577fe3dc898fc740a3999a1f1ce0'
FACEBOOK_SECRET = open(path('facebook_consumer_secret')).read().strip()

XAPIAN_LOCATION = path('xapian_db')

THUMBNAIL_DIRECTORY = path('static/thumbnails')

DEFAULT_WIDGET_CACHE_TIME = 20 # seconds

try:
    from local_settings import *
except ImportError:
    pass
