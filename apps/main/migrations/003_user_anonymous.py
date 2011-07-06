from apps.main.models import User, connection
import settings

db = connection[settings.DATABASE_NAME]
print "Fixing", db.User.find({'anonymous':{'$exists':False}}).count()
for each in db.User.find({'anonymous':{'$exists':False}}):
    each['anonymous'] = False
    each.save()
