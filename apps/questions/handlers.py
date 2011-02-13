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
        #for x in iter(form):
        #    #print type(x)
        #    print x.label
        self.render("questions/add.html", **options)

    def post(self):
        form = QuestionForm(self.request.arguments)
        raise Exception