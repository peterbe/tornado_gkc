import re
from time import mktime
import datetime
from apps.main.tests.base import BaseHTTPTestCase, TestClient
from utils import format_time_ampm
import utils.send_mail as mail

class LoginError(Exception):
    pass


class HandlersTestCase(BaseHTTPTestCase):

    pass#def setUp(self):
    #    super(EmailRemindersTestCase, self).setUp()
    #    self.client = TestClient(self)#self.get_app())
