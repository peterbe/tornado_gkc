from mongokit import RequireFieldError, ValidationError
import datetime
from tornado_utils import encrypt_password
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
        inst.password = encrypt_password('secret')
        inst.save()

        self.assertFalse(inst.check_password('Secret'))
        self.assertTrue(inst.check_password('secret'))

    def test_user_settings(self):
        user = self.db.User()
        user.username = u'peterbe'
        user.save()

        settings = self.db.UserSettings()
        self.assertRaises(RequireFieldError, settings.save)
        settings.user = user._id
        settings.save()

        self.assertFalse(settings.newsletter_opt_out)

        model = self.db.UserSettings
        self.assertEqual(model.find({'user': user._id}).count(), 1)

    def test_delete_user_deletes_settings(self):
        user = self.db.User()
        user.username = u'peterbe'
        user.save()

        settings = self.db.UserSettings()
        settings.user = user._id
        settings.save()

        assert self.db.UserSettings.find().count() == 1
        user.delete()
        self.assertEqual(self.db.UserSettings.find().count(), 0)

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

    def test_flash_message(self):
        user = self.db.User()
        user.username = u'peterbe'
        user.save()

        msg = self.db.FlashMessage()
        msg.user = user._id
        msg.title = u'Title'
        msg.validate()
        msg.save()

        self.assertEqual(msg.user.username, u'peterbe')
        self.assertEqual(msg.read, False)
        self.assertEqual(msg.text, u'')


    def test_user_by_username(self):
        user = self.db.User()
        user.username = u'peterbe'
        user.email = u'peterbe@test.com'
        user.save()

        assert user._id
        self.assertEqual(self.db.User.find_by_username('peterbe')._id,
                         user._id)

        self.assertEqual(self.db.User.find_by_username('PETERBe')._id,
                         user._id)

        self.assertTrue(self.db.User.find_by_username('xxxxx') is None)

        self.assertEqual(self.db.User.find_by_email('peterbe@test.com')._id,
                         user._id)

        self.assertEqual(self.db.User.find_by_email('PETERBE@test.com')._id,
                         user._id)

        self.assertTrue(self.db.User.find_by_email('xx@xxx') is None)
