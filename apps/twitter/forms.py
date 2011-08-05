from wtforms import fields, widgets, validators
from wtforms.widgets import html_params, escape
from cgi import escape

from apps.main.forms import BaseForm

class TextAreaWithMaxlength(widgets.TextArea):
    def __init__(self, maxlength, *args, **kwargs):
        self.maxlength = maxlength
        self.cols = kwargs.pop('cols', 60)
        self.rows = kwargs.pop('rows', 4)
        super(TextAreaWithMaxlength, self).__init__(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        kwargs.update(dict(maxlength=self.maxlength))
        if 'cols' not in kwargs:
            kwargs['cols'] = self.cols
        if 'rows' not in kwargs:
            kwargs['rows'] = self.rows
        return super(TextAreaWithMaxlength, self).__call__(*args, **kwargs)


class PostForm(BaseForm):
    message = fields.TextField("Message",
                     [validators.Required(), validators.Length(min=5, max=200)],
                     description="",
                     widget=TextAreaWithMaxlength(140),
                     id="id_message")

    def __init__(self, *args, **kwargs):
        super(PostForm, self).__init__(*args, **kwargs)
