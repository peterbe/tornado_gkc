#!/usr/bin/env python
import os
import unittest
import site

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
path = lambda *a: os.path.join(ROOT,*a)

site.addsitedir(path('vendor'))


TEST_MODULES = [
    'apps.main.tests.test_handlers',
    'apps.main.tests.test_models',
    'apps.questions.tests.test_models',
    'apps.questions.tests.test_handlers',
    'apps.play.tests.test_handlers',
    'apps.play.tests.test_models',
    'apps.play.tests.test_client',
    'apps.play.tests.test_battle',
    'apps.widget.tests.test_handlers',
    'apps.rules.tests.test_models',
]

import settings
for app_name in settings.APPS:
    __import__('apps.%s' % app_name, globals(), locals(), ['models'], -1)

def all():
    try:
        return unittest.defaultTestLoader.loadTestsFromNames(TEST_MODULES)
    except AttributeError, e:
        if "'module' object has no attribute 'test_handlers'" in str(e):
            # most likely because of an import error
            for m in TEST_MODULES:
                __import__(m, globals(), locals())
        raise


if __name__ == '__main__':
    import tornado.testing
    #import cProfile, pstats
    #cProfile.run('tornado.testing.main()')
    try:
        tornado.testing.main()
    except KeyboardInterrupt:
        pass # exit
