# this is needed for test_client
from tornado.options import define
define("start_flashpolicy", default=False, type=bool)

from test_handlers import *
from test_battle import *
from test_client import *
from test_models import *
