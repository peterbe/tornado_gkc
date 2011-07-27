from wtforms import fields, widgets, validators
#from wtforms import (Form, BooleanField, TextField, TextAreaField, validators,
#                     FileField, IntegerField)
from wtforms.widgets import html_params, escape
from cgi import escape

from apps.main.forms import BaseForm, TextInputWithMaxlength

class NumberInput(widgets.Input):
    input_type = 'number'
    size = 3
    def __call__(self, field, **kwargs):
        if 'size' not in kwargs:
            kwargs['size'] = 3
        return super(NumberInput, self).__call__(field, **kwargs)

class RulesForm(BaseForm):
    name = fields.TextField("Name",
                     [validators.Required(), validators.Length(min=5, max=60)],
                     description="",
                     widget=TextInputWithMaxlength(60),
                     id="id_name")

    no_questions = fields.IntegerField("Number of questions",
                     [validators.Required(), validators.NumberRange(min=5, max=25)],
                     description="Minimum 5, maximum 25",
                     widget=NumberInput(),
                     id="id_no_questions")

    thinking_time = fields.IntegerField("Thinking time (seconds)",
                     [validators.Required(), validators.NumberRange(min=5, max=30)],
                     description="Minimum 5, maximum 30",
                     widget=NumberInput(),
                     id="id_thinking_time")

    min_no_people = fields.IntegerField("Min. number of people",
                     [validators.Required(), validators.NumberRange(min=2, max=5)],
                     description="Minimum 2, maximum 5",
                     widget=NumberInput(),
                     id="id_min_no_people")

    max_no_people = fields.IntegerField("Max. number of people",
                     [validators.Required(), validators.NumberRange(min=2, max=5)],
                     description="Minimum 2, maximum 5",
                     widget=NumberInput(),
                     id="id_max_no_people")

    genres = fields.SelectMultipleField("Categories only", [],
                     description="If left blank, assume all published categories",
                     id="id_genres")

    pictures_only = fields.BooleanField("Pictures only",
                      description="Questions with picture only")

    alternatives_only = fields.BooleanField("Alternatives only",
                         description="Skip typing and go to alternatives immediately")

    notes = fields.TextAreaField("Notes",
                     [validators.Length(min=0, max=500)],
                     description="",
                     id="id_notes")


    def __init__(self, *args, **kwargs):
        super(RulesForm, self).__init__(*args, **kwargs)

    def set_genre_choices(self, choices):
        self.genres.choices = choices
