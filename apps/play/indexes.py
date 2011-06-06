from pymongo import ASCENDING, DESCENDING
from models import Play, PlayedQuestion
from mongokit import Connection
import settings
con = Connection()
con.register([Play, PlayedQuestion])
db = con[settings.DATABASE_NAME]

def run(**options):
    collection = db.Play.collection
    if options.get('clear_all_first'):
        collection.drop_indexes()

    collection.ensure_index('users.$id')
    yield 'users'

    collection = db.PlayedQuestion.collection
    if options.get('clear_all_first'):
        collection.drop_indexes()

    collection.ensure_index('user.$id')
    yield 'played_question.user'
    collection.ensure_index('play.$id')
    yield 'played_question.play'
    collection.ensure_index('question.$id')
    yield 'played_question.question'

    #collection.ensure_index('tags')
    #yield 'tags'
#    collection.ensure_index('author.$id')
#    yield 'author.$id'
#    collection.ensure_index('genre.$id')
#    yield 'genre.$id'

#    collection = db.Comment.collection
#    collection.ensure_index('user.$id')
#    yield 'user.$id'
#    collection.ensure_index('gist.$id')
#    yield 'gist.$id'
#    collection.ensure_index([('add_date',DESCENDING)])
#    yield 'add_date'

    test()


def test():
    any_obj_id = list(db.Play.find().limit(1))[0]._id
    curs = db.Play.find({'users.$id': any_obj_id}).explain()['cursor']
    assert 'BtreeCursor' in curs

    curs = (db.PlayedQuestion
           .find({'play.$id': any_obj_id,
                  'user.$id': any_obj_id,
                  'question.$id': any_obj_id,
                  }).explain())['cursor']
    assert 'BtreeCursor' in curs

    #curs = db.Question.find({'author.$id': any_obj_id}).explain()['cursor']
    #assert 'BtreeCursor' in curs

    #curs = db.Question.find({'state':'abc123'}).explain()['cursor']
    #assert 'BtreeCursor' in curs
