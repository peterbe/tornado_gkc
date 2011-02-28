from pymongo.objectid import InvalidId, ObjectId
import re
from random import randint
from pprint import pprint
import tornado.web
from tornado.web import HTTPError
from utils.decorators import login_required
from apps.main.handlers import BaseHandler
from utils.routes import route, route_redirect
#import constants

from models import *
from forms import QuestionForm

class QuestionsBaseHandler(BaseHandler):
    def get_base_options(self):
        options = super(QuestionsBaseHandler, self).get_base_options()
        options['page_title'] = options.get('page_title')
        return options

    def find_question(self, question_id):
        if isinstance(question_id, basestring):
            try:
                question_id = ObjectId(question_id)
            except InvalidId:
                return None
        return self.db.Question.one({'_id': question_id})

    def must_find_question(self, question_id, user):
        question = self.find_question(question_id)
        if not question:
            raise HTTPError(404, "Question can't be found")
        if question.author != user and not self.is_admin_user(user):
            raise HTTPError(404, "Not your question")
        return question

    def can_submit_question(self, question):
        if question.text and question.answer:
            if question.alternatives and len(question.alternatives) >= 4:
                return True
        return False

@route('/questions/genre_names.json$')
class QuestionsGenreNamesHandler(QuestionsBaseHandler):
    def get(self):
        names = [x.name for x in self.db.Genre.find().sort('name')]
        self.write_json(dict(names=names))

route_redirect('/questions$', '/questions/', name="questions_shortcut")
@route('/questions/$', name="questions")
class QuestionsHomeHandler(QuestionsBaseHandler):
    DEFAULT_BATCH_SIZE = 100

    @tornado.web.authenticated
    def get(self):
        options = self.get_base_options()
        user = self.get_current_user()
        _user_search = {'author.$id': user._id}
        options['accepted_questions'] = \
        self.db.Question.find({
            'author.$id': {'$ne': user._id},
            'state': ACCEPTED
        })

        options['draft_questions'] = \
        self.db.Question.find(
          dict(_user_search, state=DRAFT)).sort('add_date', -1)

        options['rejected_questions'] = \
        self.db.Question.find(
          dict(_user_search, state=REJECTED)).sort('reject_date', -1)

        if self.is_admin_user(user):
            _user_search = {}
        options['submitted_questions'] = \
        self.db.Question.find(
          dict(_user_search, state=SUBMITTED)).sort('submit_date', -1)

        self.render("questions/index.html", **options)

@route('/questions/add/$', name="add_question")
class AddQuestionHandler(QuestionsBaseHandler):

    @tornado.web.authenticated
    def get(self, form=None):
        options = self.get_base_options()
        if form is None:
            form = QuestionForm()
        options['form'] = form
        options['page_title'] = "Add question"
        self.render("questions/add.html", **options)

    @tornado.web.authenticated
    def post(self):
        data = djangolike_request_dict(self.request.arguments)
        if 'alternatives' in data:
            data['alternatives'] = ['\n'.join(data['alternatives'])]
        form = QuestionForm(data)
        if form.validate():
            #print "AFTER VALIDATE()"
            #print "text", repr(form.text.data)
            #print "answer", repr(form.answer.data)
            #print "accept", repr(form.accept.data)
            #print "alternatives", repr(form.alternatives.data.splitlines())
            #print "genre", repr(form.genre.data)
            #print "spell_correct", repr(form.spell_correct.data)
            #print "comment", repr(form.comment.data)
            #print "\n"
            question = self.db.Question()
            question.text = form.text.data
            question.answer = form.answer.data
            question.accept = [form.accept.data]
            question.alternatives = [x for x in form.alternatives.data.splitlines()]
            assert question.answer in question.alternatives, "answer not in alternatives"
            genre = self.db.Genre.one(dict(name=form.genre.data))
            if not genre:
                genre = self.db.Genre.one(dict(name=\
                  re.compile('^%s$' % re.escape(form.genre.data), re.I|re.U)))
            if not genre:
                genre = self.db.Genre()
                genre.name = form.genre.data
                genre.save()
            question.genre = genre
            question.spell_correct = form.spell_correct.data
            question.comment = form.comment.data
            question.author = self.get_current_user()
            question.state = DRAFT
            question.save()
            edit_url = self.reverse_url('edit_question', str(question._id))
            #self.redirect('/questions/%s/edit/' % question._id)
            self.redirect(edit_url)

        else:
            self.get(form=form)

class djangolike_request_dict(dict):
    def getlist(self, key):
        value = self.get(key)
        return self.get(key)


@route('/questions/(\w{24})/$', name="view_question")
class ViewQuestionHandler(QuestionsBaseHandler):

    @tornado.web.authenticated
    def get(self, question_id):
        options = self.get_base_options()
        options['question'] = self.must_find_question(question_id, options['user'])
        options['page_title'] = "View question"
        options['your_question'] = options['question'].author == options['user']
        self.render('questions/view.html', **options)


@route('/questions/(\w{24})/edit/$', name="edit_question")
class EditQuestionHandler(QuestionsBaseHandler):

    @tornado.web.authenticated
    def get(self, question_id, form=None):
        options = self.get_base_options()
        question = self.must_find_question(question_id, options['user'])
        options['question'] = question
        if form is None:
            initial = dict(question)
            initial['spell_correct'] = question.spell_correct
            initial['genre'] = question.genre.name
            form = QuestionForm(**initial)
        options['form'] = form
        options['can_submit'] = False
        if not form.errors and self.can_submit_question(question):
            options['can_submit'] = True
        options['page_title'] = "Edit question"
        self.render('questions/edit.html', **options)

    @tornado.web.authenticated
    def post(self, question_id):
        user = self.get_current_user()
        question = self.must_find_question(question_id, user)
        data = djangolike_request_dict(self.request.arguments)
        if 'alternatives' in data:
            data['alternatives'] = ['\n'.join(data['alternatives'])]
        if 'accept' in data:
            data['accept'] = ['\n'.join(data['accept'])]
        form = QuestionForm(data)
        if form.validate():
            question.text = form.text.data
            question.answer = form.answer.data
            question.accept = [x for x in form.accept.data.splitlines()]
            question.alternatives = [x for x in form.alternatives.data.splitlines()]
            assert question.answer in question.alternatives, "answer not in alternatives"
            genre = self.db.Genre.one(dict(name=form.genre.data))
            if not genre:
                genre = self.db.Genre.one(dict(name=\
                  re.compile('^%s$' % re.escape(form.genre.data), re.I|re.U)))
            if not genre:
                genre = self.db.Genre()
                genre.name = form.genre.data
                genre.save()
            question.genre = genre
            question.spell_correct = form.spell_correct.data
            question.comment = form.comment.data
            question.state = DRAFT
            question.save()
            edit_url = self.reverse_url('edit_question', str(question._id))
            #self.redirect('/questions/%s/edit/' % question._id)
            # flash message
            self.redirect(edit_url+'?msg=EDITED')

        else:
            self.get(question_id, form=form)

@route('/questions/(\w{24})/submit/$', name="submit_question")
class SubmitQuestionHandler(QuestionsBaseHandler):

    @tornado.web.authenticated
    def get(self, question_id):
        options = self.get_base_options()
        #user = self.get_current_user()
        options['question'] = self.must_find_question(question_id, options['user'])
        options['page_title'] = "Submit question"
        self.render('questions/submit.html', **options)

    @tornado.web.authenticated
    def post(self, question_id):
        user = self.get_current_user()
        question = self.must_find_question(question_id, user)
        if not self.can_submit_question(question):
            self.write("You can't submit this question. Go back to edit")
            return
        question.state = SUBMITTED
        question.submit_date = datetime.datetime.now()
        question.save()

        url = self.reverse_url('questions')
        url += '?submitted=%s' % question._id
        self.redirect(url)

@route('/questions/(\w{24})/reject/$', name="reject_question")
class RejectQuestionHandler(QuestionsBaseHandler):

    @tornado.web.authenticated
    def post(self, question_id):
        user = self.get_current_user()
        if not self.is_admin_user(user):
            raise HTTPError(403, "Not admin user")
        question = self.must_find_question(question_id, user)
        reject_comment = self.get_argument('reject_comment').strip()
        question.reject_comment = reject_comment
        question.reject_date = datetime.datetime.now()
        question.save()
        url = self.reverse_url('questions')
        url += '?rejected=%s' % question._id
        self.redirect(url)


@route('/questions/(\w{24})/accept/$', name="accept_question")
class AcceptQuestionHandler(QuestionsBaseHandler):

    @tornado.web.authenticated
    def post(self, question_id):
        user = self.get_current_user()
        if not self.is_admin_user(user):
            raise HTTPError(403, "Not admin user")
        question = self.must_find_question(question_id, user)
        question.state = ACCEPTED
        question.accept_date = datetime.datetime.now()
        question.save()
        url = self.reverse_url('view_question', question._id)
        url += '?accepted=%s' % question._id
        self.redirect(url)

@route('/questions/(\w{24})/publish/$', name="publish_question")
class PublishQuestionHandler(QuestionsBaseHandler):

    @tornado.web.authenticated
    def post(self, question_id):
        user = self.get_current_user()
        if not self.is_admin_user(user):
            raise HTTPError(403, "Not admin user")
        question = self.must_find_question(question_id, user)
        question.state = PUBLISHED
        question.publish_date = datetime.datetime.now()
        question.save()
        url = self.reverse_url('questions')
        url += '?published=%s' % question._id
        self.redirect(url)

@route('/questions/random/review/$', name="review_random")
class RandomReviewQuestionHandler(QuestionsBaseHandler):

    @tornado.web.authenticated
    def get(self):
        options = self.get_base_options()
        user = self.get_current_user()
        had_question_ids = self.get_cookie('reviewed_questions','').split('|')
        question_id = self.get_argument('question_id', None)
        question = None
        if question_id:
            question = self.find_question(question_id)
            if not question:
                raise HTTPError(404, "question not found")
            if question.state != ACCEPTED:
                raise HTTPError(404, "question not accepted")
        else:
            questions = self.db.Question.find({
                'author.$id':{'$ne':user._id},
                'state':ACCEPTED}
            )
            questions_count = questions.count()
            r = randint(0, questions_count - 1)
            for this_question in questions.sort('accept_date').limit(1).skip(r):
                #if str(this_question._id) in had_question_ids:
                #    continue
                if not self.db.QuestionReview.find({
                  'question.$id':this_question._id,
                  'user.$id':user._id,
                }).count():
                    question = this_question
                    had_question_ids.insert(0, str(question._id))
                    break

        options['buttons'] = (
          dict(name=VERIFIED, value="OK, verified"),
          dict(name=UNSURE, value="OK but unsure"),
          dict(name=WRONG, value="Wrong"),
          dict(name=TOO_EASY, value="Too easy"),
          dict(name=TOO_HARD, value="Too hard"),
        )

        options['question'] = question
        if had_question_ids:
            self.set_cookie('reviewed_questions', '|'.join(had_question_ids))
        else:
            self.clear_cookie('reviewed_questions')

        if question is None:
            options['page_title'] = "No questions to review"
            self.render("questions/nothing_to_review.html", **options)
        else:
            options['page_title'] = "Review a random question"
            self.render("questions/review.html", **options)

@route('/questions/(\w{24})/review/$', name="review_question")
class ReviewQuestionHandler(QuestionsBaseHandler):

    @tornado.web.authenticated
    def post(self, question_id):
        user = self.get_current_user()
        question = self.find_question(question_id)
        if question.state != ACCEPTED:
            raise HTTPError(400, "Question not accepted")
        if question.author == user:
            raise HTTPError(400, "Can't review your own question")
        # there can't already be a review by this user
        if self.db.QuestionReview.one({
            'user.$id': user._id,
            'question.$id': question._id}):
            raise HTTPError(400, "Already reviewed")

        raise NotImplementedError
