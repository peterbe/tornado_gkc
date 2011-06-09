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

class HighscoreBand(tornado.web.UIModule):
    def render(self, position):
        if position in (1, 2, 3):
            return position
        if position <= 10:
            return 10
        if position <= 50:
            return 50
        if position <= 100:
            return 100
        else:
            return 1000
