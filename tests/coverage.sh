#!/bin/sh

OMIT="tests,docs,$HOME/lib,setup"

coverage run --branch setup.py test
coverage report -m --omit $OMIT >| coverage.txt
cat coverage.txt
