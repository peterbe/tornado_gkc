from utils.decorators import login_required
from apps.main.handlers import BaseHandler
from utils.routes import route, route_redirect
#import constants

from forms import QuestionForm

route_redirect('/questions$', '/questions/')
@route('/questions/$')
class QuestionsHomeHandler(BaseHandler):
    DEFAULT_BATCH_SIZE = 100

    def get(self):
        options = self.get_base_options()
        user = self.get_current_user()
        if user:
            superuser = user.email == 'peterbe@gmail.com'
        else:
            superuser = False
        self.render("questions/index.html", **options)

@route('/questions/add/$')
class AddQuestionHandler(BaseHandler):

    def get(self, form=None):
        options = self.get_base_options()
        if form is None:
            form = QuestionForm(alternatives='a\nb\nc')
        options['form'] = form
        self.render("questions/add.html", **options)

    def post(self):
        data = djangolike_request_dict(self.request.arguments)
        if 'alternatives' in data:
            data['alternatives'] = ['\n'.join(data['alternatives'])]
        form = QuestionForm(data)
        if form.validate():
            print "text", repr(form.text.data)
            print "answer", repr(form.answer.data)
            print "accept", repr(form.accept.data)
            print "alternatives", repr(form.alternatives.data.splitlines())
            print "genre", repr(form.genre.data)
            print "spell_correct", repr(form.spell_correct.data)
            print "comment", repr(form.comment.data)
            raise Exception
        else:
            self.get(form=form)

class djangolike_request_dict(dict):
    def getlist(self, key):
        value = self.get(key)
        return self.get(key)