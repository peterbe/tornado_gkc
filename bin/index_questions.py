#!/usr/bin/env python

import code, re
import os, sys
if os.path.abspath(os.curdir) not in sys.path:
    sys.path.insert(0, os.path.abspath(os.curdir))

import time
import datetime
import xappy
import settings
from utils.stopwords import stopwords

import tornado.options
from tornado.options import define, options

here = os.path.abspath(os.path.dirname(__file__))
since_filename = os.path.join(here, '.indexed_document_since')
if os.path.isfile(since_filename):
    default_since = open(since_filename).read().strip()
else:
    default_since = '2011-01-01'

define("verbose", default=False, help="be louder", type=bool)
define("reindex_all", default=False, help="reindex all", type=bool)
define("test", default=False, help="do a test search afterwards", type=bool)
define("since", default=None, help="yyyy-mm-dd optional", type=unicode,
       metavar=default_since)
define("update_fields", default=False,
       help="force setting up field actions again", type=bool)

def main():
    tornado.options.parse_command_line()

    from apps.main.models import User
    from apps.questions.models import Question, Genre
    from mongokit import Connection
    con = Connection()
    con.register([Question, Genre, User])
    db = con.gkc

    if options.reindex_all:
        since = datetime.datetime(1979,12,13)
    else:
        since = options.since
        if not since:
            since = default_since
        try:
            since = datetime.datetime.strptime(since, '%Y-%m-%d %H-%M-%S')
        except ValueError:
            since = datetime.datetime.strptime(since, '%Y-%m-%d')
    if options.verbose:
        print 'since', since
    indexer = xappy.IndexerConnection(settings.XAPIAN_LOCATION)
    if not indexer.get_fields_with_actions() or options.update_fields:
        indexer.add_field_action('question', xappy.FieldActions.INDEX_FREETEXT,
                                 weight=2, language='en', spell=True,
                                 stop=stopwords)
        indexer.add_field_action('answer', xappy.FieldActions.INDEX_FREETEXT,
                                 language='en', spell=True,
                                 )
        indexer.add_field_action('accept', xappy.FieldActions.INDEX_FREETEXT,
                                 language='en', spell=True)
        indexer.add_field_action('alternatives', xappy.FieldActions.INDEX_FREETEXT,
                                 language='en', spell=True)
        indexer.add_field_action('author', xappy.FieldActions.INDEX_EXACT)
        indexer.add_field_action('genre', xappy.FieldActions.INDEX_EXACT)
        indexer.add_field_action('comment', xappy.FieldActions.INDEX_FREETEXT,
                                 language='en', spell=False, search_by_default=False,
                                 stop=stopwords)
        indexer.add_field_action('date', xappy.FieldActions.SORTABLE, type="date")
        indexer.add_field_action('state', xappy.FieldActions.SORTABLE)

        indexer.add_field_action('question', xappy.FieldActions.STORE_CONTENT)
        indexer.add_field_action('answer', xappy.FieldActions.STORE_CONTENT)
        indexer.add_field_action('genre', xappy.FieldActions.STORE_CONTENT)
        indexer.add_field_action('state', xappy.FieldActions.STORE_CONTENT)

    genres = {}
    authors = {}
    count = 0
    search = {'modify_date': {'$gt': since}}
    youngest = since
    t0 = time.time()
    for question in db.Question.collection.find(search):
        if question['modify_date'] > youngest:
           youngest = question['modify_date']
        doc = xappy.UnprocessedDocument()
        doc.fields.append(xappy.Field('state', question['state']))
        doc.fields.append(xappy.Field('question', question['text']))
        doc.fields.append(xappy.Field('answer', question['answer']))
        if question['genre'].id in genres:
            genre = genres[question['genre'].id]
        else:
            genre = db.Genre.one({'_id': question['genre'].id})
            genre = genre.name
            genres[question['genre'].id] = genre
        doc.fields.append(xappy.Field('genre', genre))
        if question['author'].id in authors:
            author = authors[question['author'].id]
        else:

            author = db.User.one({'_id': question['author'].id})
            author = author.username
            authors[question['author'].id] = author
        print repr(author)
        doc.fields.append(xappy.Field('author', author))
        doc.fields.append(xappy.Field('comment', question['comment']))
        doc.fields.append(xappy.Field('accept', '\n'.join(question['accept'])))
        doc.fields.append(xappy.Field('alternatives', '\n'.join(question['alternatives'])))
        doc.id = str(question['_id'])
        pdoc = indexer.process(doc)
        indexer.replace(pdoc)
        count += 1
        #if count and not count % 100:
        #    indexer.flush()
    # add a second to avoid milliseconds causing the same doc to be index over and over
    youngest += datetime.timedelta(seconds=1)
    open(since_filename, 'w').write(youngest.strftime('%Y-%m-%d %H-%M-%S\n'))

    indexer.flush()
    t1 = time.time()
    indexer.close()
    if options.verbose:
        print round(t1-t0, 3), "seconds to index", count, "questions"

    # test
    if options.test:
        searcher = xappy.SearchConnection(settings.XAPIAN_LOCATION)
        text = 'FRAMCEs capitalls'
        text = "Capitol STATE"
        print searcher.spell_correct(text)
        query = searcher.query_field('question', text, default_op=searcher.OP_OR)
        results = searcher.search(query, 0, 10)
        print results.matches_estimated
        #print results.estimate_is_exact
        for result in results:
            print result.rank, result.id
            print repr(result.summarise('question')), result.data['state'][0]
            #result.data['state']


if __name__ == '__main__':
    main()
