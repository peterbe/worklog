#!/usr/bin/env python
import unittest

TEST_MODULES = [
    'tests.test_app',
    'tests.test_api',
    'tests.test_models',
    'tests.test_utils',
]

def all():
    try:
        return unittest.defaultTestLoader.loadTestsFromNames(TEST_MODULES)
    except AttributeError, e:
        if "'module' object has no attribute 'test_app'" in str(e):
            # most likely because of an import error
            for m in TEST_MODULES:
                __import__(m, globals(), locals())
        raise
        

if __name__ == '__main__':
    import tornado.testing
    #import cProfile, pstats
    #cProfile.run('tornado.testing.main()')
    tornado.testing.main()