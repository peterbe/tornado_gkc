from pymongo import ASCENDING, DESCENDING
from models import Question, Genre, QuestionReview, QuestionPoints
from mongokit import Connection
import settings
con = Connection()
con.register([Question, Genre, QuestionReview, QuestionPoints])
db = con[settings.DATABASE_NAME]

def run(**options):
    def ensure(coll, arg):
        coll.ensure_index(arg,
                          background=options.get('background', False))

    collection = db.Question.collection
    if options.get('clear_all_first'):
        collection.drop_indexes()

    ensure(collection, 'state')
    yield 'state'
    ensure(collection, 'author.$id')
    yield 'author.$id'
    ensure(collection, 'genre.$id')
    yield 'genre.$id'

    test()


def test():
    any_obj_id = list(db.Question.find().limit(1))[0]._id
    curs = db.Question.find({'genre.$id': any_obj_id}).explain()['cursor']
    assert 'BtreeCursor' in curs

    curs = db.Question.find({'author.$id': any_obj_id}).explain()['cursor']
    assert 'BtreeCursor' in curs

    curs = db.Question.find({'state':'abc123'}).explain()['cursor']
    assert 'BtreeCursor' in curs
