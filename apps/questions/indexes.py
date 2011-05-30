from pymongo import ASCENDING, DESCENDING
from models import Question, Genre, QuestionReview, QuestionPoints
from mongokit import Connection
import settings
con = Connection()
con.register([Question, Genre, QuestionReview, QuestionPoints])
db = con[settings.DATABASE_NAME]

def run(**options):
    collection = db.Question.collection
    if options.get('clear_all_first'):
        collection.drop_indexes()

    collection.ensure_index('state')
    yield 'state'
    #collection.ensure_index('tags')
    #yield 'tags'
    collection.ensure_index('author.$id')
    yield 'author.$id'
    collection.ensure_index('genre.$id')
    yield 'genre.$id'

#    collection = db.Comment.collection
#    collection.ensure_index('user.$id')
#    yield 'user.$id'
#    collection.ensure_index('gist.$id')
#    yield 'gist.$id'
#    collection.ensure_index([('add_date',DESCENDING)])
#    yield 'add_date'

    test()


def test():
    any_obj_id = list(db.Question.find().limit(1))[0]._id
    curs = db.Question.find({'genre.$id': any_obj_id}).explain()['cursor']
    assert 'BtreeCursor' in curs

    curs = db.Question.find({'author.$id': any_obj_id}).explain()['cursor']
    assert 'BtreeCursor' in curs

    curs = db.Question.find({'state':'abc123'}).explain()['cursor']
    assert 'BtreeCursor' in curs
