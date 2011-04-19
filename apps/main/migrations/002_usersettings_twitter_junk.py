from apps.main.models import UserSettings
from mongokit import Connection
import settings
con = Connection()
con.register([UserSettings])

db = con[settings.DATABASE_NAME]
print "Fixing", db.UserSettings.find({'twitter_access_token':{'$exists':True}}).count()
for each in db.UserSettings.find({'twitter_access_token':{'$exists':True}}):
    del each['twitter_access_token']
    del each['twitter_profile_image_url']
    each.save()
