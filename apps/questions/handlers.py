from pymongo.objectid import InvalidId, ObjectId
import re
import datetime
import logging
from random import randint
from pprint import pprint
import tornado.web
from tornado.web import HTTPError
from utils.decorators import login_required, login_redirect
from apps.main.handlers import BaseHandler
from utils.routes import route, route_redirect
from utils.send_mail import send_email
import settings

from models import STATES, DRAFT, SUBMITTED, REJECTED, ACCEPTED, PUBLISHED
from models import VERDICTS, VERIFIED, UNSURE, WRONG, TOO_EASY, TOO_HARD

from forms import QuestionForm

class QuestionsBaseHandler(BaseHandler):
    def get_base_options(self):
        options = super(QuestionsBaseHandler, self).get_base_options()

        options['page_title'] = options.get('page_title')
        if options['user']:
            options['total_question_points'] = self.get_total_questions_points(options['user'])
        else:
            options['total_question_points'] = 0
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
            raise HTTPError(403, "Not your question")
        return question

    def can_submit_question(self, question):
        if question.state not in (DRAFT, REJECTED):
            return False
        if question.text and question.answer:
            if question.alternatives and len(question.alternatives) >= 4:
                return True
        return False

    def can_edit_question(self, question, user):
        if question.state in (DRAFT, REJECTED):
            if question.author == user:
                return True
            elif self.is_admin_user(user):
                return True
        return False

    def get_questions_counts(self, user):
        F = lambda x:self.db.Question.find(x).count()
        R = lambda x:self.db.QuestionReview.find(x).count()
        author_search = {'author.$id': user._id}
        user_search = {'user.$id': user._id}
        data = {
          'published': F(dict(author_search, state=PUBLISHED)),
          'accepted': F(dict(author_search, state=ACCEPTED)),
          'rejected': F(dict(author_search, state=REJECTED)),
          'reviewed': R(dict(user_search)),
        }
        return data

    QUESTION_VALUES = {
      'published': 10,
      'accepted': 5,
      'reviewed': 1,
      'rejected': -5,
    }

    def get_total_questions_points(self, user):
        total_points = 0
        for key, count in self.get_questions_counts(user).items():
            value = self.QUESTION_VALUES[key]
            points = value * count
            total_points += points
        return total_points

@route('/questions/points/', name='question_points')
class QuestionPointsHandler(QuestionsBaseHandler):

    @login_redirect
    def get(self):
        options = self.get_base_options()

        data = self.get_questions_counts(options['user'])
        total_points = 0

        for key in data:
            value = self.QUESTION_VALUES[key]
            points = value * data[key]
            options[key] = data[key]
            options['%s_value' % key] = value
            options['%s_points' % key] = points
            total_points += points
        options['total_points'] = total_points

        options['page_title'] = "Breakdown of your Question Points"
        self.render('questions/points.html', **options)


@route('/questions/genre_names.json$', name="genre_names_json")
class QuestionsGenreNamesHandler(QuestionsBaseHandler):
    def get(self):
        names = [x.name for x in self.db.Genre.find().sort('name')]
        self.write_json(dict(names=names))

route_redirect('/questions$', '/questions/', name="questions_shortcut")
@route('/questions/$', name="questions")
class QuestionsHomeHandler(QuestionsBaseHandler):
    DEFAULT_BATCH_SIZE = 20

    @tornado.web.authenticated
    def get(self):
        options = self.get_base_options()
        options['page_title'] = "Questions dashboard"
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
            self.push_flash_message("Question added",
              "Your question has been added and can now be edited")
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
        options['reviews'] = []

        # to avoid NameErrors
        options['rating_total'] = None
        options['difficulty_total'] = None
        options['skip'] = None
        options['can_edit'] = False

        if self.can_edit_question(options['question'], options['user']):
            options['can_edit'] = True

        self.render('questions/view.html', **options)


@route('/questions/(\w{24})/edit/$', name="edit_question")
class EditQuestionHandler(QuestionsBaseHandler):


    @tornado.web.authenticated
    def get(self, question_id, form=None):
        options = self.get_base_options()
        question = self.must_find_question(question_id, options['user'])
        if not self.can_edit_question(question, options['user']):
            raise HTTPError(403, "Can't edit this question")
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
        if not self.can_edit_question(question, user):
            raise HTTPError(403, "Can't edit this question")
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
            if question.answer not in question.alternatives:
                alts = []
                for each in question.alternatives:
                    if each.lower() == form.answer.data.lower():
                        alts.append(form.answer.data)
                    else:
                        alts.append(each)
                question.alternatives = alts
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

            if self.get_argument('submit_question', False):
                assert self.can_submit_question(question), "can't submit question"
                question.state = SUBMITTED
                question.submit_date = datetime.datetime.now()
                question.save()

                self.push_flash_message("Question submitted!",
                  "Your question has now been submitted and awaits to be accepted for review.")

                question_url = 'http://%s%s' % \
                  (self.request.host, self.reverse_url('view_question', question._id))
                try:
                    email_body = "New question submitted:\n%s\n\n--\n%s\n" % \
                      (question_url, settings.PROJECT_TITLE)
                    send_email(self.application.settings['email_backend'],
                               "%s has submitted a question" % user.username,
                               email_body,
                               self.application.settings['webmaster'],
                               self.application.settings['admin_emails'],
                    )
                except:
                    logging.error("Unable to send email about submitted question %s"\
                      % question_url, exc_info=True)

                url = self.reverse_url('questions')
                self.redirect(url)
            else:
                edit_url = self.reverse_url('edit_question', str(question._id))
                #self.redirect('/questions/%s/edit/' % question._id)

                if self.can_submit_question(question):
                    self.push_flash_message("Question edited!",
                     "Question is ready to be submitted")
                else:
                    self.push_flash_message("Question edited!",
                     "Question is not yet ready to be submitted")

                # flash message
                self.redirect(edit_url)

        else:
            self.get(question_id, form=form)

@route('/questions/(\w{24})/submit/$', name="submit_question")
class SubmitQuestionHandler(QuestionsBaseHandler):

    @tornado.web.authenticated
    def get(self, question_id):
        options = self.get_base_options()
        question = self.must_find_question(question_id, options['user'])
        options['question'] = question
        if question.state not in (DRAFT, REJECTED):
            if question.author == options['user']:
                raise HTTPError(403, "Not your question")
            elif not self.is_admin_user(options['user']):
                raise HTTPError(403, "Not your question")
        options['page_title'] = "Submit question"
        self.render('questions/submit.html', **options)

    @tornado.web.authenticated
    def post(self, question_id):
        user = self.get_current_user()
        question = self.must_find_question(question_id, user)
        if question.state not in (DRAFT, REJECTED):
            if question.author == user:
                return self.redirect(self.reverse_url('view_question', question._id))
            elif not self.is_admin_user(user):
                raise HTTPError(403, "Not your question")
        if not self.can_submit_question(question):
            raise HTTPError(400, "You can't submit this question. Go back to edit")
        question.state = SUBMITTED
        question.submit_date = datetime.datetime.now()
        question.save()

        self.push_flash_message("Question submitted!",
            "Your question has now been submitted and awaits to be accepted for review.")

        question_url = 'http://%s%s' % \
                  (self.request.host, self.reverse_url('view_question', question._id))
        try:
            email_body = "New question submitted:\n%s\n\n--\n%s\n" % \
              (question_url, settings.PROJECT_TITLE)
            send_email(self.application.settings['email_backend'],
                       "%s has submitted a question" % user.username,
                       email_body,
                       self.application.settings['webmaster'],
                       self.application.settings['admin_emails'],
            )
        except:
            logging.error("Unable to send email about submitted question %s"\
              % question_url, exc_info=True)
        url = self.reverse_url('questions')
        self.redirect(url)

@route('/questions/(\w{24})/reject/$', name="reject_question")
class RejectQuestionHandler(QuestionsBaseHandler):

    @tornado.web.authenticated
    def post(self, question_id):
        user = self.get_current_user()
        if not self.is_admin_user(user):
            raise HTTPError(403, "Not admin user")
        question = self.must_find_question(question_id, user)
        reject_comment = self.get_argument('reject_comment', u'').strip()
        question.reject_comment = reject_comment
        question.reject_date = datetime.datetime.now()
        question.state = REJECTED
        question.save()

        # XXX Need ability here to send an email to the question owner!!
        self.push_flash_message("Question rejected!",
            "Question owner needs to amend the question.")

        edit_question_url = 'http://%s%s' % \
          (self.request.host, self.reverse_url('edit_question', question._id))
        try:
            if question.author.email:
                email_body = 'Sorry but the question you added ("%s") had to '\
                             'be rejected.\n' % question.text
                if reject_comment:
                    email_body += 'Comment: %s\n\n' % reject_comment
                email_body += "To edit the question again go to:\n%s\n" %\
                  edit_question_url
                email_body += "\n--\n%s\n" % settings.PROJECT_TITLE
                send_email(self.application.settings['email_backend'],
                           "%s has submitted a question" % user.username,
                           email_body,
                           self.application.settings['webmaster'],
                           [question.author.email],
                )
        except:
            logging.error("Unable to send email about rejected question %s"\
              % question_url, exc_info=True)

        url = self.reverse_url('questions')
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

        self.push_flash_message("Question accepted!",
            "Question is now ready to be peer reviewed")

        url = self.reverse_url('view_question', question._id)
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

        self.push_flash_message("Question published!",
            "Question is now ready for game play!")

        if 1:
            url = self.reverse_url('review_accepted')
        else:
            url = self.reverse_url('questions')
        self.redirect(url)

@route('/questions/review/random/$', name="review_random")
class RandomReviewQuestionHandler(QuestionsBaseHandler):

    @tornado.web.authenticated
    def get(self):
        options = self.get_base_options()
        user = self.get_current_user()
        had_question_ids = self.get_cookie('reviewed_questions','').split('|')
        had_question_ids = [x.strip() for x in had_question_ids if x.strip()]
        question_id = self.get_argument('question_id', None)
        question = None
        if question_id:
            question = self.find_question(question_id)
            if not question:
                raise HTTPError(404, "question not found")
            if question.state != ACCEPTED:
                raise HTTPError(404, "question not accepted")
        else:
            accept_search = {'author.$id':{'$ne':user._id},
                             'state':ACCEPTED}
            questions = self.db.Question.find(accept_search)
            questions_count = questions.count()
            if questions_count >= 1:
                count_rejections = 0
                previous_rs = set()
                while True:
                    r = randint(0, questions_count - 1)
                    while r in previous_rs:
                        r = randint(0, questions_count - 1)
                    questions = self.db.Question.find(accept_search)
                    previous_rs.add(r)
                    for this_question in questions.sort('accept_date').limit(1).skip(r):
                        #if str(this_question._id) in had_question_ids:
                        #    continue
                        if self.db.QuestionReview.find({
                          'question.$id':this_question._id,
                          'user.$id':user._id,
                        }).count():
                            count_rejections += 1
                        else:
                            question = this_question
                            had_question_ids.insert(0, str(question._id))
                            break
                    if count_rejections >= questions_count or question:
                        break

        options['buttons'] = (
          dict(name=VERIFIED, value="Answer verified"),
          dict(name=UNSURE, value="Unsure about answer"),
          dict(name=WRONG, value="Wrong"),
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

        rating = self.get_argument('rating', 'OK')
        rating_to_int = {'Bad':-1, 'OK':0, 'Good':1}
        if rating not in rating_to_int:
            raise HTTPError(404, "Invalid rating")
        rating = rating_to_int[rating]
        difficulty = int(self.get_argument('difficulty', 0))
        if difficulty not in (-1, 0, 1):
            raise HTTPError(400, "Invalid difficulty")
        comment = self.get_argument('comment', u'').strip()
        verdict = self.get_argument('verdict')
        if verdict not in VERDICTS:
            raise HTTPError(404, "Invalid verdict")

        review = self.db.QuestionReview()
        review.question = question
        review.user = user
        review.verdict = verdict
        review.rating = rating
        review.difficulty = difficulty
        review.comment = comment
        review.save()

        self.push_flash_message("Question reviewed!",
            "Thank you for adding your review")

        url = self.reverse_url('review_random')
        self.redirect(url)


@route('/questions/review/accepted/$', name="review_accepted")
class AcceptedReviewQuestionHandler(QuestionsBaseHandler):

    @tornado.web.authenticated
    def get(self):
        options = self.get_base_options()
        user = self.get_current_user()
        if not self.is_admin_user(user):
            raise HTTPError(403)

        skip = int(self.get_argument('skip', 0))
        options['skip'] = skip
        questions = self.db.Question.find({'state': ACCEPTED})\
          .skip(skip).limit(1).sort('accept_date', -1)
        question = None
        for question in questions:
            options['question'] = question

        if question:
            options['reviews'] = self.db.QuestionReview.find({'question.$id':question._id}).sort('add_date', 1)
            ratings = [x.rating for x in options['reviews']]
            options['reviews'].rewind()
            difficulties = [x.difficulty for x in options['reviews'] if x.difficulty is not None]
            options['reviews'].rewind()
            if ratings:
                options['rating_total'] = str(sum(ratings))
            else:
                options['rating_total'] = '-'

            if difficulties:
                options['difficulty_total'] = str(sum(difficulties))
            else:
                options['difficulty_total'] = '-'
            options['page_title'] = "Review accepted question"
            options['can_edit'] = self.can_edit_question(question, options['user'])

            self.render("questions/view.html", **options)
        else:
            options['page_title'] = "No questions to review"
            self.render("questions/nothing_to_review.html", **options)

    @tornado.web.authenticated
    def post(self):
        skip = int(self.get_argument('skip'))
        self.redirect(self.reverse_url('review_accepted') + "?skip=%d" % (skip + 1))


route_redirect('/questions/all$', '/questions/all/', name="all_questions_shortcut")
@route('/questions/all/$', name="all_questions")
class AllQuestionsHomeHandler(QuestionsBaseHandler): # pragma: no cover

    @tornado.web.authenticated
    def get(self):
        options = self.get_base_options()
        options['all_questions'] = self.db.Question.find().sort('add_date', 1)
        options['page_title'] = "All questions (admin eyes only)"

        state_counts = []
        for state in STATES:
            c = self.db.Question.find({'state':state}).count()
            state_counts.append((state, c))
        _total = sum(x[1] for x in state_counts)
        state_counts = [(state, count, round(100.0*count/_total,0))
          for (state, count) in state_counts]
        options['state_counts'] = state_counts

        try:
            from pygooglechart import PieChart2D
            chart = PieChart2D(400, 250)
            chart.fill_solid(PieChart2D.BACKGROUND, '000000')
            chart.add_data([x[1] for x in state_counts])
            chart.set_pie_labels([x[0] for x in state_counts])
            options['state_counts_pie'] = chart.get_url()
        except ImportError:
            options['state_counts_pie'] = None

        self.render("questions/all.html", **options)
