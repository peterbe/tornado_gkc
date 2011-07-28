#!/usr/bin/env python
import os, sys
p = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if p not in sys.path:
    sys.path.insert(0, p)

from urllib import urlopen
import tornado.options
from tornado.options import define, options
import settings

define("verbose", default=False, help="be louder", type=bool)
define("all", default=False, help="rerender all question images", type=bool)
define("questions", default=10, help="no. question images", type=int)
define("random", default=False, help="pick random", type=bool)
define("domain", default="kwissle.com", help="domain name", type=str)

def main(*args):
    tornado.options.parse_command_line()
    from apps.main.models import User, connection
    from apps.questions.models import DRAFT, Question, QuestionImage
    db = connection.gkc

    if options.all:
        max = 999999
    else:
        max = options.questions

    question_images = []
    if options.random:
        while len(question_images) < max:
            qi = db.QuestionImage.find_random()
            if qi.question.state != DRAFT:
                question_images.append(qi)
    else:
        for qi in db.QuestionImage.find().limit(max):
            if qi.question.state != DRAFT:
                question_images.append(qi)
                if len(question_images) >= max:
                    break

    base_url = 'http://%s' % options.domain
    for question_image in question_images:
        url = base_url + '/questions/image/%s/render/' % question_image._id
        url += '?force-refresh=1'
        print url
        print urlopen(url).read()


if __name__ == '__main__':
    import sys
    sys.exit(main(*sys.argv[1:]))
