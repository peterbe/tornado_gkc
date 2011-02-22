from pymongo.objectid import InvalidId, ObjectId
import re
from pprint import pprint
import tornado.web
from utils.decorators import login_required
from apps.main.handlers import BaseHandler
from utils.routes import route, route_redirect
#import constants

from forms import QuestionForm

class QuestionsBaseHandler(BaseHandler):
    def find_question(self, question_id):
        if isinstance(question_id, basestring):
            try:
                question_id = ObjectId(question_id)
            except InvalidId:
                return None
        return self.db.Question.one({'_id': question_id})


route_redirect('/questions$', '/questions/', name="questions_shortcut")
@route('/questions/$', name="questions")
class QuestionsHomeHandler(QuestionsBaseHandler):
    DEFAULT_BATCH_SIZE = 100

    def get(self):
        options = self.get_base_options()
        user = self.get_current_user()
        if user:
            superuser = user.email == 'peterbe@gmail.com'
        else:
            superuser = False
        self.render("questions/index.html", **options)

@route('/questions/add/$', name="add_question")
class AddQuestionHandler(QuestionsBaseHandler):

    @tornado.web.authenticated
    def get(self, form=None):
        options = self.get_base_options()
        if form is None:
            form = QuestionForm(alternatives='a\nb\nc')
        options['form'] = form
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


@route('/questions/(\w{24})/edit/$', name="edit_question")
class EditQuestionHandler(QuestionsBaseHandler):

    @tornado.web.authenticated
    def get(self, question_id, form=None):
        options = self.get_base_options()
        user = self.get_current_user()
        question = self.find_question(question_id)
        if not question:
            raise tornado.web.HTTPError(404, "Question can't be found")
        if question.author != user and not self.is_admin_user(user):
            raise tornado.web.HTTPError(404, "Not your question")

        options['question'] = question
        if form is None:
            initial = dict(question)
            initial['spell_correct'] = question.spell_correct
            initial['genre'] = question.genre.name
            form = QuestionForm(**initial)
        options['form'] = form
        self.render('questions/edit.html', **options)

    @tornado.web.authenticated
    def post(self, question_id):
        user = self.get_current_user()
        question = self.find_question(question_id)
        if not question:
            raise tornado.web.HTTPError(404, "Question can't be found")
        if question.author != user or self.is_admin_user(user):
            raise tornado.web.HTTPError(404, "Not your question")
        data = djangolike_request_dict(self.request.arguments)
        if 'alternatives' in data:
            data['alternatives'] = ['\n'.join(data['alternatives'])]
        form = QuestionForm(data)
        if form.validate():
            question.test = form.text.data
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
            question.save()
            edit_url = self.reverse_url('edit_question', str(question._id))
            #self.redirect('/questions/%s/edit/' % question._id)
            # flash message
            self.redirect(edit_url+'?msg=EDITED')

        else:
            self.get(question_id, form=form)
