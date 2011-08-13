import datetime
from apps.rules.models import Rules
from apps.main.models import User
from apps.main.tests.base import BaseModelsTestCase

class ModelsTestCase(BaseModelsTestCase):

    def test_basic_creation(self):
        rules = self.db.Rules()
        rules.name = u'My fun rules'
        rules.save()

        self.assertEqual(rules.genres.count(), 0)
        self.assertEqual(rules.author, None)

        peppe = self.db.User()
        peppe.username = u'peppe'
        peppe.save()
        rules.author = peppe._id
        rules.save()
        self.assertEqual(rules.author, peppe)

        maths = self.db.Genre()
        maths.name = u'Maths'
        maths.save()
        rules['genres'].append(maths._id)
        rules.save()

        self.assertEqual(rules.genres.count(), 1)
        self.assertEqual(list(rules.genres), [maths])
