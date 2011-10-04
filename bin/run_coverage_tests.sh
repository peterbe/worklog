#!/bin/bash

python bin/_run_coverage_tests.py
if [ "$?" == 0 ]; then
  open coverage_report/index.html
fi
