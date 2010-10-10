#!/bin/bash

python _run_coverage_tests.py
if [ "$?" == 0 ]; then
  xdg-open coverage_report/index.html
fi