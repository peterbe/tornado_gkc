from wtforms import Form, BooleanField, TextField, TextAreaField, validators
from wtforms.widgets import html_params, escape, TextInput
from cgi import escape

from apps.main.forms import BaseForm

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
        _removed_title = False
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
            if not _removed_title:
                if 'title' in kwargs:
                    kwargs.pop('title')
                _removed_title = True
            htmls.append(html)
            if self.vertical:
                htmls.append('<br/>')
        return '\n'.join(htmls)

class TextInputWithMaxlength(TextInput):
    def __init__(self, maxlength, *args, **kwargs):
        self.maxlength = maxlength
        super(TextInputWithMaxlength, self).__init__(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        kwargs.update(dict(maxlength=self.maxlength))
        return super(TextInputWithMaxlength, self).__call__(*args, **kwargs)

class QuestionForm(BaseForm):
    text = TextField("Question", [validators.Required(),
                              validators.Length(min=5, max=60)],
                     description="Make sure the question ends with a ?",
                     widget=TextInputWithMaxlength(60),
                     id="id_text")
    answer = TextField("Answer", [validators.Required(),
                                  validators.Length(min=1, max=15)],
                      description="Make it reasonably short and easy to type",
                      widget=TextInputWithMaxlength(15),
                      id="id_answer")
    accept = TextAreaField("Also accept (aliases for the correct answer)", widget=MultilinesWidget(length=3, vertical=True),
                           description="Other answers that are also correct")
    alternatives = TextAreaField("Alternatives (1 correct, 3 incorrect ones)", [validators.Required()],
                                 description="The answer has to be one of the alternatives",
                                 widget=MultilinesWidget(length=4))
    genre = TextField("Category (most popular ones, feel free to use Other)", [validators.Required()],
                      description='Try to use big groups like "Geography" instead of "European capitals"')
    spell_correct = BooleanField("Allow spelling mistakes", description="Whether small spelling mistakes should be accepted")
    comment = TextAreaField("Comment",
                            description="Any references or links to strengthen your answer")

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
