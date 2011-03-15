from apps.questions.models import Question
from mongokit import Connection
con = Connection()
con.register([Question])


collection = con.gkc[Question.__collection__]
print "Fixing", collection.Question.find({'difficulty':{'$exists': False}}).count(), "objects"
for each in collection.Question.find({'difficulty':{'$exists': False}}):
    each['difficulty'] = u"MEDIUM"
    each['language'] = u'en-gb'
    each.save()
