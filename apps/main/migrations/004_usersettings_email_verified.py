from apps.main.models import User, UserSettings, connection
import settings

db = connection[settings.DATABASE_NAME]

qs = db.UserSettings.find({'email_verified':{'$exists':False}})
print "Fixing", qs.count()
for each in qs:
    each['email_verified'] = None
    each.save()

for u in db.User.find():
    if u.email:
        us = db.UserSettings.one({'user.$id': u._id})
        if not us:
            us = db.UserSettings()
            us.user = u
        us.email_verified = u.email
        us.save()
