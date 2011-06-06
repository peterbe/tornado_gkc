from pymongo import ASCENDING, DESCENDING
from models import User, UserSettings
from mongokit import Connection
import settings
con = Connection()
con.register([User, UserSettings])
db = con[settings.DATABASE_NAME]

def run(**options):
    def ensure(coll, arg):
        coll.ensure_index(arg,
                          background=options.get('background', False))

    collection = db.User.collection
    if options.get('clear_all_first'):
        collection.drop_indexes()
    ensure(collection, 'username')
    yield 'username'

    test()


def test():
    any_obj_id = list(db.User.find().limit(1))[0]._id
    curs = db.User.find({'_id': any_obj_id}).explain()['cursor']

    assert 'BtreeCursor' in curs

    curs = db.User.find({'username': u'peterbe'}).explain()['cursor']
    assert 'BtreeCursor' in curs

    curs = db.UserSettings.find({'user.$id': any_obj_id}).explain()['cursor']
    assert 'BtreeCursor' in curs
