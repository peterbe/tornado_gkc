from pymongo import ASCENDING, DESCENDING
from models import Play, PlayedQuestion
from mongokit import Connection
import settings
con = Connection()
con.register([Play, PlayedQuestion])
db = con[settings.DATABASE_NAME]

def run(**options):
    def ensure(collection, arg):
        collection.ensure_index(arg, background=options.get('background', False))

    collection = db.Play.collection
    if options.get('clear_all_first'):
        collection.drop_indexes()

    ensure(collection, 'users.$id')
    yield 'users'

    collection = db.PlayedQuestion.collection
    if options.get('clear_all_first'):
        collection.drop_indexes()

    ensure(collection, 'user.$id')
    yield 'played_question.user'
    ensure(collection, 'play.$id')
    yield 'played_question.play'
    ensure(collection, 'question.$id')
    yield 'played_question.question'

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
