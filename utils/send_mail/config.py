EMAIL_HOST = 'smtp.elasticemail.com'
EMAIL_PORT = 2525

EMAIL_HOST_USER = 'mail@peterbe.com'
EMAIL_HOST_PASSWORD = '57252e4d-f87b-4e1a-a3d3-c5a6bfea5ea0'

EMAIL_USE_TLS = False

import os
op = os.path
PICKLE_LOCATION = op.join(op.dirname(__file__), 'pickled_messages')
if not op.isdir(PICKLE_LOCATION):
    os.mkdir(PICKLE_LOCATION)
