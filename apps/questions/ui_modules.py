import tornado.web


class RenderField(tornado.web.UIModule):
    def render(self, field):
        try:
            return field(title=field.description)
        except TypeError:
            return field()

class QuestionShortStats(tornado.web.UIModule):
    def render(self, question):
        return dict(foo='bar')
