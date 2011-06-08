from mongokit import RequireFieldError, ValidationError
import datetime
from apps.main.models import UserSettings
from base import BaseModelsTestCase


class ModelsTestCase(BaseModelsTestCase):

    def test_create_user(self):
        user = self.db.User()
        user.username = u'peterbe'
        assert user.add_date
        assert user.modify_date
        user.save()

        inst = self.db.users.User.one()
        assert inst.username
        from utils import encrypt_password
        inst.password = encrypt_password('secret')
        inst.save()

        self.assertFalse(inst.check_password('Secret'))
        self.assertTrue(inst.check_password('secret'))

    def test_user_settings(self):
        user = self.db.User()
        user.username = u'peterbe'
        settings = self.db.UserSettings()

        self.assertRaises(RequireFieldError, settings.save)
        settings.user = user
        settings.save()

        self.assertFalse(settings.newsletter_opt_out)

        model = self.db.UserSettings
        self.assertEqual(model.find({'user.$id': user._id}).count(), 1)

    def test_usersettings_bool_keys(self):

        keys = UserSettings.get_bool_keys()
        self.assertTrue(isinstance(keys, list))
        self.assertTrue(keys) # at least one
        self.assertTrue(isinstance(keys[0], basestring))

    def test_updating_modify_date(self):
        user = self.db.User()
        user.username = u'peter'
        user.save()
        diff = user.modify_date - user.add_date
        highest = max(user.modify_date, user.add_date)
        lowest = min(user.modify_date, user.add_date)
        diff = highest - lowest
        milliseconds = diff.microseconds / 1000.0
        assert milliseconds < 0.1

        from time import sleep
        sleep(0.1)
        user.username = u'other'
        user.save()

        user = self.db.User.one({'username': u'other'})
        self.assertTrue(user.modify_date > user.add_date)
        diff = user.modify_date - user.add_date
        milliseconds = diff.microseconds / 1000.0
        self.assertTrue(diff.microseconds >= 100)
