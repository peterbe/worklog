About worklog
=============

To run the unit tests
---------------------

You can either run the tests one-off like this:

        ./runtests.py
	
Or keep it running waiting for changes:

        ./runtests.py --autoreload
	
To run the tests of an individual test module, you can do this:

        ./runtests.py tests.test_models
        or
        ./runtests.py tests.test_models.ModelsTestCase
        or 
        ./runtests.py tests.test_models.ModelsTestCase.test_create_user
        
        