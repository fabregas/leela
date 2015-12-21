#!/usr/bin/python

import sys
import os

if len(sys.argv) != 2:
    print('Usage: %s <version>'%sys.argv[0])
    sys.exit(1)

open('leela/__init__.py', 'w').write('__version__ = "%s"'%sys.argv[1])
ret = os.system('git add leela/__init__.py')
if ret:
    print('ERROR! "git add" failed!')
    sys.exit(1)

ret = os.system("git commit -m 'updated version file (%s)'"%sys.argv[1])

ret = os.system('git tag %s -a'%sys.argv[1])
if ret:
    print('ERROR! "git tag" failed!')
    sys.exit(1)

