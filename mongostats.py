## FROM:
##  http://www.djcinnovations.com/archives/84

import pymongo

"""mongostats.py

   Prints statistics summarizing the frequency of each key
   in every collection of a Mongo database.  Helpful as a
   diagnostic tool.
"""

# 'map' function in JavaScript
# emits (key, 1) for each key present in a document
map_fn = """
function () {
  for (key in this) {
    emit(key, 1);
  }
};
"""

# 'reduce' function in JavaScript
# totals the counts associated with a given key
reduce_fn = """
function (key, values) {
  var sum = 0;
  for each (value in values) {
     sum += value;
  }
  return sum;
};
"""

# set these appropriately for your connection & database
connection = pymongo.Connection("localhost", slave_okay=True)
database = connection.worklog

# find all collections in the database
collnames = database.collection_names()

# loop over collections names
for collname in collnames:
    collection = database[collname]

    # count all documents in this collection
    total = collection.count()

    # use map/reduce to count the frequency of each field
    result = collection.map_reduce(map_fn, reduce_fn)

    # print out the summary data
    print collname.center(60, '=')
    for item in result.find():
        key = item['_id']
        count = int(item['value'])
        freq = (count / float(total)) * 100.0
        print "    %-20.20s : %8i / %8i (%6.2f%%)" % (key, count, total, freq)