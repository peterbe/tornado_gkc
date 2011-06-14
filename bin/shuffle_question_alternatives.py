#!/usr/bin/env python
import os, sys
p = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if p not in sys.path:
    sys.path.insert(0, p)

from collections import defaultdict
from pprint import pprint
import random

import tornado.options
from tornado.options import define, options

define("verbose", default=False, help="be louder", type=bool)
define("questions", default=20, help="no. questions", type=int)
define("random", default=False, help="pick random questions", type=bool)

def main(*args):
    tornado.options.parse_command_line()
    from apps.questions.models import Question
    from mongokit import Connection
    con = Connection()
    con.register([Question])
    db = con.gkc
    positions = defaultdict(int)
    limit = options.questions

    last_index = None
    def shuffle(question, last_index):
        alternatives = question.alternatives
        random.shuffle(alternatives)
        index = alternatives.index(question.answer)
        while index == last_index:
            random.shuffle(alternatives)
            index = alternatives.index(question.answer)
        question.alternatives = alternatives

        if 0:#options.verbose:
            print repr(question.text)
            print alternatives, repr(question.answer)
        positions[index] += 1
        question.save(update_modify_date=False)
        return index

    if options.random:
        count = 0
        while count < limit:
            question = db.Question.find_random()
            if question.state == 'PUBLISHED':
                last_index = shuffle(question, last_index)
                count += 1
    else:
        for question in (db.Question
                         .find({'state':'PUBLISHED'})
                         .sort('modify_date', -1)
                         .limit(limit)):
            last_index = shuffle(question, last_index)

    max_ = max(positions.values())
    if options.verbose:
        for k in sorted(positions):
            v = positions[k] / float(max_)
            print k+1, '*' * int(v * 80)

if __name__ == '__main__':
    import sys
    sys.exit(main(*sys.argv[1:]))
