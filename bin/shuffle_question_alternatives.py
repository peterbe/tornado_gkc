#!/usr/bin/env python
import os, sys
if os.path.abspath(os.curdir) not in sys.path:
    sys.path.insert(0, os.path.abspath(os.curdir))

from collections import defaultdict
from pprint import pprint
from random import shuffle

def main(*args):
    from apps.questions.models import Question
    from mongokit import Connection
    con = Connection()
    con.register([Question])
    db = con.gkc
    positions = defaultdict(int)
    for question in db.Question.find({'state':'PUBLISHED'}):
        alternatives = question.alternatives
        shuffle(alternatives)
        question.alternatives = alternatives
        index = alternatives.index(question.answer)
        if 0:
            print repr(question.text)
            print alternatives, repr(question.answer)

        positions[index] += 1
    max_ = max(positions.values())
    for k in sorted(positions):
        v = positions[k] / float(max_)
        print k+1, '*' * int(v * 80)

if __name__ == '__main__':
    import sys
    sys.exit(main(*sys.argv[1:]))
