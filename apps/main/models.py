from hashlib import md5
import uuid
import datetime
from mongokit import Document, ValidationError
from utils import encrypt_password

class BaseDocument(Document):
    structure = {
      'add_date': datetime.datetime,
      'modify_date': datetime.datetime,
    }

    default_values = {
      'add_date': datetime.datetime.now,
      'modify_date': datetime.datetime.now
    }
    use_autorefs = True
    use_dot_notation = True

class User(BaseDocument):
    __collection__ = 'users'
    structure = {
      'username': unicode,
      'email': unicode,
      'password': unicode,
      'first_name': unicode,
      'last_name': unicode,
    }

    use_autorefs = True
    required_fields = ['username']
    default_values = {
    }

    indexes = [
      {'fields': 'username',
       'unique': True},
    ]

    def set_password(self, raw_password):
        self.password = encrypt_password(raw_password)

    def check_password(self, raw_password):
        """
        Returns a boolean of whether the raw_password was correct. Handles
        encryption formats behind the scenes.
        """
        if '$bcrypt$' in self.password:
            import bcrypt
            hashed = self.password.split('$bcrypt$')[-1].encode('utf8')
            return hashed == bcrypt.hashpw(raw_password, hashed)
        else:
            raise NotImplementedError("No checking clear text passwords")

class UserSettings(BaseDocument):
    __collection__ = 'user_settings'
    structure = {
      'user': User,
      'disable_sound': bool,
      'newsletter_opt_out': bool,
      'twitter': dict,
      'facebook': dict,
      'google': dict,
    }
    use_autorefs = True

    required_fields = ['user']
    default_values = {
      'disable_sound': False,
      'newsletter_opt_out': False,
    }

    validators = {
    }

    indexes = [
      {'fields': 'user.$id',
       'check': False,
       'unique': True},
    ]

    @staticmethod
    def get_bool_keys():
        return [key for (key, value)
                in UserSettings.structure.items()
                if value is bool]


class FlashMessage(BaseDocument):
    __collection__ = 'flash_messages'
    structure = {
      'user': User,
      'title': unicode,
      'text': unicode,
      'read': bool,
    }
    default_values = {
      'read': False,
      'text': u'',
    }
    required_fields = ['user', 'title']
    indexes = [
      {'fields': 'user.$id',
       'check': False},
      {'fields': 'read'},
    ]
