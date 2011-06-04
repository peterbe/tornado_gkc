import tornado.web

from apps.play.forms import PlayMessageForm

class SendPlayMessageForm(tornado.web.UIModule):
    def render(self, play):
        user = self.handler.get_current_user()
        options = {
          'play': play,
          'user': user,
          'form': PlayMessageForm(),
          'other_user': play.get_other_user(user),
        }
        return self.render_string("play/add_play_message.html", **options)
