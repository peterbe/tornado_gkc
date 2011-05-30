#!/usr/bin/env python
import os, sys
if os.path.abspath(os.curdir) not in sys.path:
    sys.path.insert(0, os.path.abspath(os.curdir))

def main(*apps):

    if '--help' in apps:
        print "python %s [app [, app2]] [--clear-all-first]" % __file__
        return 0

    clear_all_first = False
    if '--clear-all-first' in apps:
        clear_all_first = True
        apps = list(apps)
        apps.remove('--clear-all-first')

    if not apps:
        apps = [x for x in os.listdir('apps')
                if (os.path.isdir(os.path.join('apps', x)) and
                    os.path.isfile(os.path.join('apps', x, 'indexes.py')))]

    for app in apps:
        _indexes = __import__('apps.%s' % app, globals(), locals(), ['indexes'], -1)
        runner = _indexes.indexes.run
        print app
        print '\t', ', '.join(runner(clear_all_first=clear_all_first))

    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main(*sys.argv[1:]))
