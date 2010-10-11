About worklog
=============

To run the unit tests
---------------------

You can either run the tests one-off like this:

        ./run_tests.sh

Or keep it running waiting for changes:

        ./run_tests.sh --autoreload
	
To run the tests of an individual test module, you can do this:

        ./run_tests.sh tests.test_models
        or
        ./run_tests.sh tests.test_models.ModelsTestCase
        or 
        ./run_tests.sh tests.test_models.ModelsTestCase.test_create_user
        
To run the coverage tests
-------------------------

You start it like this:

        ./run_coverage_tests.sh
	
It will cancel the report if the tests don't pass.	