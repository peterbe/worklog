About worklog
=============

Dependencies, installation
--------------------------

See INSTALL.txt


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


Getting a copy of the live database
-----------------------------------

First log in to the server:

        $ ssh tornado@donecal.fry-it.com
	
and run mongodump anywhere:

	$ cd /tmp/
	$ mongodump -d worklog
	
Then copy those files to the local server:

        $ cd /tmp
        $ jan_rsync donecal.fry-it.com:/tmp/dump .
	
Now you need to create a new database and start mongodb.

        $ cd ~/worklog
	$ mkdir live-db
	$ jed start_mongodb.sh
	$ ./start_mongodb.sh
	
Now, run the restore:

        $ ~/worklog/mongodb/bin/mongorestore dump
	
	