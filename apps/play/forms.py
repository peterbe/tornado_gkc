from wtforms import Form, BooleanField, TextField, TextAreaField, validators
from wtforms.widgets import html_params, escape, TextInput
from cgi import escape

from apps.main.forms import BaseForm, TextInputWithMaxlength

class PlayMessageForm(BaseForm):
    message = TextField("Message",
                        [validators.Required(),
                         validators.Length(min=2, max=100)],
                        description="",
                        widget=TextInputWithMaxlength(100),
                        id="id_message",
                        )
