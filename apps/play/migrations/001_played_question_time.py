from time import sleep
from apps.main.models import connection
from apps.play.models import PlayedQuestion

collection = connection.gkc[PlayedQuestion.__collection__]
print "Fixing", collection.PlayedQuestion.find({'time':{'$exists': False}}).count(), "objects"

while collection.PlayedQuestion.find({'time':{'$exists': False}}).count():
    for each in (collection.PlayedQuestion
                 .find({'time':{'$exists': False}})
                 .limit(1000)):
        each['time'] = None
        each.save()
        print "Done 1000, taking a quick break"
        sleep(1)
