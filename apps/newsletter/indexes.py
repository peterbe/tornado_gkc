from pymongo import ASCENDING, DESCENDING
from apps.main.models import connection
from models import NewsletterSettings
import settings
db = connection[settings.DATABASE_NAME]

def run(**options):
    def ensure(collection, arg):
        collection.ensure_index(arg,
          background=options.get('background', False))

    collection = db.NewsletterSettings.collection
    if options.get('clear_all_first'):
        collection.drop_indexes()

    ensure(collection, 'next_send')
    yield 'next_send'

    test()


def test():
    import datetime
    then = datetime.datetime.now() - datetime.timedelta(days=199)
    curs = (db.NewsletterSettings.find({'next_send': {'$gte': then}})
            .explain()['cursor'])
    assert 'BtreeCursor' in curs
