#!/usr/bin/env python
import here

import tornado.options
from tornado.options import define, options
import settings


def main(*args):
    tornado.options.parse_command_line()
    from apps.main.models import connection
    from apps.questions.models import DRAFT, Question, QuestionImage
    db = connection.gkc

    for q in db.QuestionImage.collection.find():
        if not db.Question.collection.one({'_id': q['question'].id}):
            print repr(q['question'].id)
            db.QuestionImage.collection.remove(q['_id'])


if __name__ == '__main__':
    import sys
    sys.exit(main(*sys.argv[1:]))
