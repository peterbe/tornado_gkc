import datetime
from apps.main.models import BaseDocument, User

class ChatMessage(BaseDocument):
    __collection__ = 'chat_messages'
    structure = {
      'user': User,
      'message': unicode,
    }
