#!/usr/bin/env python
import os, sys
if os.path.abspath(os.curdir) not in sys.path:
    sys.path.insert(0, os.path.abspath(os.curdir))

import unittest

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
]

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
