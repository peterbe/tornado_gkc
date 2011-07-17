#!/usr/bin/env python
import os, sys
p = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if p not in sys.path:
    sys.path.insert(0, p)

import tornado.options
from tornado.options import define, options
import settings

template = """
<script src="%(src)s"></script>
"""
def main(*args):
    tornado.options.parse_command_line()
    from utils.tornado_static import run_closure_compiler

    op = os.path
    root_dir = op.abspath(op.join(op.dirname(__file__), '..'))
    full_path = op.join(root_dir, 'static/js/widget.js')
    save_full_path = op.join(root_dir, 'widget.js')
    code = run_closure_compiler(
      open(full_path).read(),
      op.join(root_dir, 'static', 'compiler.jar'),
      verbose=True
    )
    code = '// To find out more about this, go to http://kwissle.com\n%s' % code
    try:
        existing = open(save_full_path).read()
    except IOError:
        existing = None
    if existing != code:
        open(save_full_path, 'w').write(code.strip() + '\n')

    cdn_full_path = op.join(root_dir, 'cdn_prefix.conf')
    try:
        cdn_prefix = [x.strip() for x in file(cdn_full_path)
                         if x.strip() and not x.strip().startswith('#')][0]
    except (IOError, IndexError):
        cdn_prefix = None
    src = ((cdn_prefix if cdn_prefix else '//kwissle.com') +
           '/widget.js')
    html = template % dict(src=src)
    print html

if __name__ == '__main__':
    import sys
    sys.exit(main(*sys.argv[1:]))
