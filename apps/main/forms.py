from wtforms import Form, BooleanField, TextField, TextAreaField, validators, SelectField
from wtforms.widgets import html_params, escape, TextInput

class BaseForm(Form):
    def validate(self, *args, **kwargs):
        for name, f in self._fields.iteritems():
            if isinstance(f.data, str):
                f.data = unicode(f.data, 'utf-8')
            if isinstance(f.data, basestring):
                f.data = f.data.strip()
        return super(BaseForm, self).validate(*args, **kwargs)


class TextInputWithMaxlength(TextInput):
    def __init__(self, maxlength, *args, **kwargs):
        self.maxlength = maxlength
        super(TextInputWithMaxlength, self).__init__(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        kwargs.update(dict(maxlength=self.maxlength))
        return super(TextInputWithMaxlength, self).__call__(*args, **kwargs)


class SettingsForm(BaseForm):
    email = TextField("E-mail", [validators.Email()])
    first_name = TextField("First name")
    last_name = TextField("Last name")
    newsletter_frequency = SelectField("Newsletter frequency")

    def __init__(self, newsletter_frequency_options=None, *args, **kwargs):
        super(SettingsForm, self).__init__(*args, **kwargs)
        if not newsletter_frequency_options:
            del self.newsletter_frequency
        else:
            choices = [(x, x) for x in newsletter_frequency_options]
            self.newsletter_frequency.choices = choices
