from utils.decorators import login_required
from apps.main.handlers import BaseHandler
from utils.routes import route, route_redirect
#import constants

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
