import datetime
from bson.objectid import ObjectId
from apps.main.models import BaseDocument, register


FREQUENCIES = (
  'daily',
  'weekly',
  'bi-weekly',
  'monthly',
  'quarterly',
)

@register
class NewsletterSettings(BaseDocument):
    __collection__ = 'newsletters'
    structure = {
      'user': ObjectId,
      'opt_out': bool,
      'frequency': unicode,
      'last_send': datetime.datetime,
      'next_send': datetime.datetime,
    }
    use_autorefs = True

    required_fields = ['user']
    default_values = {
      'opt_out': False,
      'frequency': u'weekly',
      'next_send': (datetime.datetime.utcnow() +
                    datetime.timedelta(days=7)),
    }

    validators = {
      'frequency': lambda x: x in FREQUENCIES,
    }
