from wtforms import fields, validators

from apps.main.forms import BaseForm, TextInputWithMaxlength


class PlayMessageForm(BaseForm):
    message = fields.TextField("Message",
                        [validators.Required(),
                         validators.Length(min=2, max=100)],
                        description="",
                        widget=TextInputWithMaxlength(100),
                        id="id_message",
                        )
