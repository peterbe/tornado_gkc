import random
import logging
import time
from bson.objectid import ObjectId, InvalidId
from tornado_utils.routes import route
from apps.main.handlers import BaseHandler
from apps.questions.models import PUBLISHED
from tornado.web import HTTPError
import settings
from utils import dict_plus


@route('/widget/preview/$', name='widget_preview')
class PreviewHandler(BaseHandler):

    def get(self):
        options = self.get_base_options()
        options['page_title'] = 'Preview widget'
        options['host_name'] = 'gkc'
        self.render('widget/preview.html', **options)

_last_question = None


@route('/widget/random/jsonp$', name='widget_random_question_jsonp')
class RandomQuestionHandler(BaseHandler):

    def get(self):
        question = self._get_question()
        package = dict(id=str(question._id),
                       text=question.text,
                       alts=question.alternatives)
        jsonp_callback = self.get_argument('callback', 'callback')
        self.write_jsonp(jsonp_callback, package)

    def _get_question(self, force_refresh=False,
                      cache_for=settings.DEFAULT_WIDGET_CACHE_TIME):
        search = {'state': PUBLISHED}
        global _last_question
        if _last_question and not force_refresh:
            ts, question_id = _last_question
            if ts > time.time():
                print "Reusing same old question"
                question = (self.db.Question.collection
                             .one({'_id': question_id}))
                return dict_plus(question)

        #'_id':{'$nin': [x._id for x in battle.sent_questions]}
        count = self.db.Question.find(search).count()
        while True:
            skip = random.randint(0, count - 1)
            for question in (self.db.Question.collection
                             .find(search)
                             .skip(skip)
                             .limit(1)):
                if (self.db.QuestionImage
                    .one({'question.$id': question['_id']})):
                    if '_id' not in search:
                        search['_id'] = {'$nin': []}
                    search['_id']['$nin'].append(question['_id'])
                    continue
                question = dict_plus(question)
                #logging.info("New widget question: %r (%s)"%
                #             (question.text, question._id))
                _last_question = (time.time() + cache_for, question._id)
                return question


@route('/widget/answer/$', name='widget_answer')
class AnswerHandler(BaseHandler):

    def check_xsrf_cookie(self):  # pragma: no cover
        pass

    def get(self):
        self.redirect('/')

    def post(self):
        _id = self.get_argument('id')
        try:
            question = self.db.Question.one({'_id': ObjectId(_id)})
        except InvalidId:
            raise HTTPError(400, "Invalid ID")
        if not question:
            raise HTTPError(404, "Question not found")
        if self.get_argument('answer', ''):
            answer = self.get_argument('answer')
            alternatives = False
        else:
            answer = self.get_argument('alt_answer', '')
            alternatives = True

        right = question.check_answer(answer)
        qk = (self.db.QuestionKnowledge.collection
              .one({'question.$id': question._id}))
        qk_comment = qk_alternatives_comment = None
        if qk:
            qk = dict_plus(qk)
            p_right = min(99, 100 * qk.right * 1.5)
            p_right = int(p_right)
            if right:
                if p_right < 50:
                    qk_comment = TEMPLATES[0] % dict(p_right=p_right)
                    if p_right < 20:
                        qk_comment += "You're really smart!"
                    else:
                        qk_comment += "You're smart!"
                else:
                    qk_comment = TEMPLATES[2] % dict(p_right=p_right)
            else:
                if p_right < 50:
                    qk_comment = TEMPLATES[1] % dict(p_right=p_right)
                else:
                    qk_comment = TEMPLATES[3] % dict(p_right=p_right)

        options = self.get_base_options()
        if answer:
            if right:
                if alternatives:
                    options['page_title'] = 'Very good!'
                else:
                    options['page_title'] = 'Excellent!'
            else:
                options['page_title'] = 'Sorry, better luck next time'
        else:
            options['page_title'] = 'No answer :('

        options['right'] = right
        options['alternatives'] = alternatives
        options['question'] = question
        options['knowledge_comment'] = qk_comment
        options['qk_alternatives_comment'] = qk_alternatives_comment

        _log = "Widget answer: %r " % answer
        if alternatives:
            _log += ' (alternatives)'
        if right:
            _log += ' RIGHT!'
        else:
            _log += ' WRONG'
        _log += ' Question: %r' % question.text
        _log += ' knowledge_comment: %r' % qk_comment
        logging.info(_log)
        self.render('widget/answer.html', **options)


TEMPLATES = (
"""You know, only <strong>%(p_right)s%%</strong> of Kwissle players knew
the answer to that question.
""",

"""Don't worry, only <strong>%(p_right)s%%</strong> of Kwissle players knew
the answer to that question.
""",

"""Actually, <strong>%(p_right)s%%</strong> of Kwissle players knew the answer
to that question.""",

"""About <strong>%(p_right)s%%</strong> of Kwissle players knew the answer
to that question.""",

)
