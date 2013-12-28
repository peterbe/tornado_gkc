#!/usr/bin/env python

import code, re
import here

if __name__ == '__main__':

    from apps.main.models import *
    from apps.main import models

    from apps.questions.models import Question, Genre, QuestionReview
    from apps.play.models import Play, PlayedQuestion, PlayMessage, PlayPoints
    from mongokit import Connection, Document as mongokit_Document
    from bson.objectid import ObjectId, InvalidId
    con = Connection()

    import settings
    model_classes = []
    for app_name in settings.APPS:
        _models = __import__('apps.%s' % app_name, globals(), locals(),
                                 ['models'], -1)
        try:
            models = _models.models
        except AttributeError:
            # this app simply doesn't have a models.py file
            continue
        for name in [x for x in dir(models) if re.findall('[A-Z]\w+', x)]:
            thing = getattr(models, name)
            try:
                if issubclass(thing, mongokit_Document):
                    model_classes.append(thing)
            except TypeError:
                pass

    con.register(model_classes)


    db = con.gkc
    print "AVAILABLE:"
    print '\n'.join(['\t%s'%x for x in locals().keys()
                     if re.findall('[A-Z]\w+|db|con', x)])
    print "Database available as 'db'"
    code.interact(local=locals())
