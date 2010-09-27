#!/usr/bin/env python
import unittest

TEST_MODULES = [
    'tests.test_app',
    'tests.test_models',
]

def all():
    return unittest.defaultTestLoader.loadTestsFromNames(TEST_MODULES)

if __name__ == '__main__':
    import tornado.testing
    tornado.testing.main()
