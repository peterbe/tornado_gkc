import os
import re
import bcrypt
import datetime
import random


def get_question_slug_url(question):
    question_text = question['text']
    question_text = question_text.replace(';',' ')
    question_text = question_text.replace("'",'')
    question_text = question_text.replace('  ',' ')
    if '+' in question_text:
        # probably an arithmatic question
        question_text = question_text.replace(' ','_')
    else:
        question_text = question_text.replace(' ','-')
    if question_text.endswith('?'):
        question_text = question_text[:-1]
    return '/%s/%s?' % (question['_id'], question_text)


class dict_plus(dict):
    def __init__(self, *args, **kwargs):
        if 'collection' in kwargs: # excess we don't need
            kwargs.pop('collection')
        dict.__init__(self, *args, **kwargs)
        self._wrap_internal_dicts()
    def _wrap_internal_dicts(self):
        for key, value in self.items():
            if isinstance(value, dict):
                self[key] = dict_plus(value)

    def __getattr__(self, key):
        return self[key]
