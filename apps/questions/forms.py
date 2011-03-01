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

        value = field.data
        if isinstance(value, basestring):
            values = [x.strip() for x in value.splitlines() if x.strip()]
        else:
            values = value
        #print "__call__ values", repr(values)
        for i in range(self.length):
            if values is None:
                value = u''
            else:
                try:
                    value = values[i]
                except IndexError:
                    value = u''
            kwargs['value'] = value
            kwargs_copy = dict(kwargs, id='%s_%s' % (kwargs['id'], i))
            html = '<input %s />' % html_params(name=field.name, **kwargs_copy)
            htmls.append(html)
            if self.vertical:
                htmls.append('<br/>')
        return '\n'.join(htmls)

class BaseForm(Form):
    def validate(self, *args, **kwargs):
        for name, f in self._fields.iteritems():
            if isinstance(f.data, str):
                f.data = unicode(f.data, 'utf-8')
            if isinstance(f.data, basestring):
                f.data = f.data.strip()
        return super(BaseForm, self).validate(*args, **kwargs)

class QuestionForm(BaseForm):
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

    def validate(self, *args, **kwargs):
        success = super(QuestionForm, self).validate(*args, **kwargs)
        if success:
            # check invariants
            if self.data['answer'].lower() not in self.data['alternatives'].lower():
                self._fields['alternatives'].errors.append("Answer not in alternatives")
                success = False
        return success

class EditQuestionForm(QuestionForm):
    pass
