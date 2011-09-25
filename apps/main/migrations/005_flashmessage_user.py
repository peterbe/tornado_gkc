from pymongo.objectid import ObjectId
from apps.main.models import User, FlashMessage, connection
import settings

db = connection[settings.DATABASE_NAME]

c = 0
for msg in db.FlashMessage.find():
    if type(msg['user']) is not ObjectId:
        msg['user'] = msg['user'].id
        msg.save()
        c += 1

print "Fixed", c
