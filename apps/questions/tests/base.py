from apps.questions.models import Question, QuestionReview, Genre
from apps.main.tests.base import BaseModelsTestCase as orig_BaseModelsTestCase
class BaseModelsTestCase(orig_BaseModelsTestCase):
    def setUp(self):
        super(BaseModelsTestCase, self).setUp()
        self.db.connection.register([Question, QuestionReview, Genre])
