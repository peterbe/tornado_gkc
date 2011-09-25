#!/usr/bin/env python
from here import ROOT
import os

def main(*apps):

    if '--help' in apps:
        print "python %s [app [, app2]] [--background] [--clear-all-first]" % __file__
        return 0

    background = False
    if '--background' in apps:
        background = True
        apps = list(apps)
        apps.remove('--background')

    clear_all_first = False
    if '--clear-all-first' in apps:
        clear_all_first = True
        apps = list(apps)
        apps.remove('--clear-all-first')

    if not apps:
        apps = [x for x in os.listdir(os.path.join(ROOT, 'apps'))
                if (os.path.isdir(os.path.join(ROOT, 'apps', x)) and
                    os.path.isfile(os.path.join(ROOT, 'apps', x, 'indexes.py')))]

    for app in apps:
        _indexes = __import__('apps.%s' % app, globals(), locals(), ['indexes'], -1)
        runner = _indexes.indexes.run
        print app
        print '\t', ', '.join(runner(clear_all_first=clear_all_first,
                                     background=background))

    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main(*sys.argv[1:]))
