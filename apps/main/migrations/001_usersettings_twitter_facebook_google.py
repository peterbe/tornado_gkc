from apps.main.models import UserSettings
from mongokit import Connection
import settings
con = Connection()
con.register([UserSettings])

db = con[settings.DATABASE_NAME]
print "Fixing", db.UserSettings.find({'twitter':{'$exists':False}}).count()
for each in db.UserSettings.find({'twitter':{'$exists':False}}):
    each['twitter'] = {}
    each['facebook'] = {}
    each['google'] = {}
    each.save()
