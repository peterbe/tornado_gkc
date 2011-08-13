from pymongo import ASCENDING, DESCENDING
from apps.main.models import connection
from models import Play, PlayedQuestion, PlayPoints
import settings
db = connection[settings.DATABASE_NAME]


def run(**options):
    def ensure(collection, arg):
        collection.ensure_index(arg,
          background=options.get('background', False))

    collection = db.Play.collection
    if options.get('clear_all_first'):
        collection.drop_indexes()

    ensure(collection, 'users.$id')
    yield 'users'

    ensure(collection, 'finished')
    yield 'finished'

    collection = db.PlayedQuestion.collection
    if options.get('clear_all_first'):
        collection.drop_indexes()

    ensure(collection, 'user.$id')
    yield 'played_question.user'
    ensure(collection, 'play.$id')
    yield 'played_question.play'
    ensure(collection, 'question.$id')
    yield 'played_question.question'

    collection = db.PlayPoints.collection
    if options.get('clear_all_first'):
        collection.drop_indexes()
    ensure(collection, 'user.$id')
    yield 'playpoints.user'
    ensure(collection, 'points')
    yield 'playpoints.points'

    test()


def test():
    any_obj_id = list(db.Play.find().limit(1))[0]._id
    curs = db.Play.find({'users.$id': any_obj_id}).explain()['cursor']
    assert 'BtreeCursor' in curs

    import datetime
    then = datetime.datetime.now() - datetime.timedelta(days=99)
    curs = (db.Play.find({'finished': {'$gte': then}})
            .sort('finished', -1).explain()['cursor'])
    assert 'BtreeCursor' in curs

    curs = (db.PlayedQuestion
           .find({'play.$id': any_obj_id,
                  'user.$id': any_obj_id,
                  'question.$id': any_obj_id,
                  }).explain())['cursor']
    assert 'BtreeCursor' in curs

    curs = db.PlayPoints.find({'user.$id': any_obj_id}).explain()['cursor']
    assert 'BtreeCursor' in curs

    curs = (db.PlayPoints
              .find({'points': {'$gt': 0}})
              .sort('points', -1)
              .explain()['cursor'])
    assert 'BtreeCursor' in curs

    #curs = db.Question.find({'author.$id': any_obj_id}).explain()['cursor']
    #assert 'BtreeCursor' in curs

    #curs = db.Question.find({'state':'abc123'}).explain()['cursor']
    #assert 'BtreeCursor' in curs
