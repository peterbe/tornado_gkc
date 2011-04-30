from apps.main.models import UserSettings
from mongokit import Connection
import settings
con = Connection()
con.register([UserSettings])

db = con[settings.DATABASE_NAME]
print "Fixing", db.UserSettings.find({'twitter':{'$exists':False}}).count()
for each in db.UserSettings.find({'twitter':{'$exists':False}}):
    del each['twitter_access_token']
    del each['twitter_profile_image_url']
    each['twitter'] = None
    each['facebook'] = None
    each['google'] = None
    each.save()
