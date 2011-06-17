#!/usr/bin/env python
import os, sys
p = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if p not in sys.path:
    sys.path.insert(0, p)

from pprint import pprint

import tornado.options
from tornado.options import define, options

define("verbose", default=False, help="be louder", type=bool)
define("questions", default=20, help="no. questions", type=int)
define("random", default=False, help="pick random questions", type=bool)
define("ids", help="question ids", type=str)

from collections import defaultdict
from utils import dict_plus
def calculate_knowledge(db, question):
    bot_ids = [bot['_id'] for bot in
              db.User.collection.find({'username':'BOT'})]
    users = defaultdict(set)
    tally = {
      'right': 0,
      'wrong': 0,
      'alternatives_wrong': 0,
      'alternatives_right': 0,
      'too_slow': 0,
      'timed_out': 0,
      'users': 0,
    }
    finished_plays = {}
    for played_question in (db.PlayedQuestion.collection
                              .find({'question.$id': question._id,
                                     'user.$id': {'$nin': bot_ids}})
                              .sort('add_date', 1)):
        played_question = dict_plus(played_question)
        # only bother with played questions in a play that finished
        play_id = played_question.play.id
        if play_id not in finished_plays:
            # need to figure out if it was finished
            play = db.Play.collection.one({'_id': play_id})
            assert play, play_id
            finished_plays[play_id] = bool(play['finished'])
        if not finished_plays[play_id]:
            continue
        user_id = played_question['user'].id
        if played_question['question'].id in users[user_id]:
            continue
        users[user_id].add(played_question['question'].id)
        #print "THIS"
        #pprint(played_question)

        tally['users'] += 1
        if played_question.right:
            # means, this user nailed it!
            if played_question.alternatives:
                # ...but had to load alternatives
                tally['alternatives_right'] += 1
            else:
                # ...by knowing the answer
                tally['right'] += 1
        elif played_question.answer:
            if played_question.alternatives:
                tally['alternatives_wrong'] += 1
            else:
                tally['wrong'] += 1
        else:
            # that means that this user was either
            # too slow (ie. beaten) or timed out

            # To find out what happened we need to find out how the other
            # opponent faired
            others_right = []
            others_wrong = []
            others_alternatives = []
            others_right_alternatives = []
            others_too_slow = []
            others_timed_out = []
            for other in (db.PlayedQuestion.collection
                          .find({'question.$id': question._id,
                                 'play.$id': played_question['play'].id,
                                 'user.$id': {'$ne': user_id}})
                          ):
                # always assume N opponents
                others_right.append(other['right'])
            if any(others_right):
                # in some way, the opponent beat you to it
                tally['too_slow'] += 1
            else:
                # opponent didn't get it right and you no answer
                tally['timed_out'] += 1

    if not tally['users']:
        if options.verbose:
            print "NO ANSWERS!"
            print repr(question.text), repr(question.answer)
            print question.publish_date
    else:
        if options.verbose:
            print repr(question.text), repr(question.answer)
            pprint(tally)
        check = (tally['right'] + tally['alternatives_right'] +
                 tally['wrong'] + tally['alternatives_wrong'] +
                 tally['too_slow'] + tally['timed_out'])
        if check != tally['users']:
            raise ValueError(tally)
        # save all of this!
        knowledge = db.QuestionKnowledge.one({'question.$id': question._id})
        if not knowledge:
            knowledge = db.QuestionKnowledge()
            knowledge.question = question
        users = float(tally['users'])
        knowledge.users = tally['users']
        knowledge.right = tally['right'] / users
        knowledge.wrong = tally['wrong'] / users
        knowledge.alternatives_right = tally['alternatives_right'] / users
        knowledge.alternatives_wrong = tally['alternatives_wrong'] / users
        knowledge.too_slow = tally['too_slow'] / users
        knowledge.timed_out = tally['timed_out'] / users
        knowledge.save()


def main(*args):
    tornado.options.parse_command_line()
    from apps.main.models import connection
    import apps.questions.models
    import apps.play.models
    db = connection.gkc

    limit = options.questions
    if options.ids:
        import re
        from pymongo.objectid import ObjectId
        ids = [x for x in re.split('(\w+)', options.ids)
                 if len(x.strip()) > 1]
        ids = [ObjectId(x) for x in ids]
        for question in db.Question.find({'_id': {'$in': ids}}):
            calculate_knowledge(db, question)
    elif options.random:
        count = 0
        while count < limit:
            question = db.Question.find_random()
            if question.state == 'PUBLISHED':
                calculate_knowledge(db, question)
                count += 1
    else:
        for question in (db.Question
                         .find({'state':'PUBLISHED'})
                         .sort('add_date')
                         .limit(limit)):
            calculate_knowledge(db, question)


if __name__ == '__main__':
    import sys
    sys.exit(main(*sys.argv[1:]))
