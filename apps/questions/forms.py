from wtforms import Form, BooleanField, TextField, TextAreaField, validators
from wtforms.widgets import html_params, escape, TextInput
from cgi import escape

class MultilinesWidget(object):
    def __init__(self, length=4, vertical=False):
        self.length = length
        self.vertical = vertical

    def __call__(self, field, **kwargs):
        kwargs.setdefault('id', field.id)
        htmls = []
        #print dir(field)

        value = field.data
        #print "kwargs", kwargs
        #print "data", repr(field.data)
        #print "__call__ value", repr(value)
        print "VALUE", value
        if isinstance(value, basestring):
            values = [x.strip() for x in value.splitlines() if x.strip()]
        else:
            values = value
            print "V", value
        #print "__call__ values", repr(values)
        for i in range(self.length):
            try:
                value = values[i]
            except IndexError:
                value = u''
            kwargs['value'] = value
            html = '<input %s />' % html_params(name=field.name, **kwargs)
            htmls.append(html)
            if self.vertical:
                htmls.append('<br/>')
        return '\n'.join(htmls)

class QuestionForm(Form):
    text = TextField("Text", [validators.Required(),
                              validators.Length(min=5, max=100)],
                     id="id_text")
    answer = TextField("Answer", [validators.Required(),
                                  validators.Length(min=1, max=25)],
                      id="id_answer")
    accept = TextAreaField("Also accept", widget=MultilinesWidget(length=3, vertical=True))
    alternatives = TextAreaField("Alternatives (exactly 4)", [validators.Required()],
                                 widget=MultilinesWidget(length=4))
    genre = TextField("Genre", [validators.Required()])
    spell_correct = BooleanField("Spell correct", description="Whether small spelling mistakes should be accepted")
    comment = TextAreaField("Comment")
