PROJECT_TITLE = u"Kwissle"
APPS = (
  'main',
  'questions',
  'play',
)

LOGIN_URL = "/auth/login/"
NODE_URL = "http://%(host)s:8888/battle"

COOKIE_SECRET = "12orTzK2XQAGUYdkL5gmueJIFuY37EQn92XsTo1v/Vo="

WEBMASTER = 'peterbe@gmail.com'
ADMIN_EMAILS = ['peterbe@gmail.com']

TWITTER_CONSUMER_KEY = 'UcZ80RJk7x4FVWE0d93ig'
TWITTER_CONSUMER_SECRET = open('twitter_consumer_secret').read().strip()
