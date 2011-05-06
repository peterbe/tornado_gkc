from apps.questions.models import Question, Genre
from mongokit import Connection
con = Connection()
con.register([Question, Genre])

collection = con.gkc[Genre.__collection__]

print "Fixing", collection.Genre.find({'approved':{'$exists': False}}).count(), "objects"
for each in collection.Genre.find({'approved':{'$exists': False}}):
    if con.gkc.Question.find({'state':'PUBLISHED', 'genre.$id':each['_id']}).count():
        each['approved'] = True
    else:
        each['approved'] = False
    each.save()
