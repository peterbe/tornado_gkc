#!/bin/bash

python bin/_run_coverage_tests.py
if [ "$?" == 0 ]; then
  #xdg-open coverage_report/index.html
  #firefox coverage_report/index.html
  open coverage_report/index.html
fi
