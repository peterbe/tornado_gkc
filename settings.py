TITLE = u"GKC"
APPS = (
  'main',
  'questions',
)

LOGIN_URL = "/auth/login/"

COOKIE_SECRET = "12orTzK2XQAGUYdkL5gmueJIFuY37EQn92XsTo1v/Vo="

WEBMASTER = 'peterbe@gmail.com'
ADMIN_EMAILS = ['peterbe@gmail.com']


TWITTER_CONSUMER_KEY = 'UcZ80RJk7x4FVWE0d93ig'
TWITTER_CONSUMER_SECRET = open('twitter_consumer_secret').read().strip()