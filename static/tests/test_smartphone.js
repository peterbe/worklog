test("LengthDescriber, hours", function() {
   var r = LengthDescriber.describe_hours(1);
   equals(r, "1 hour");
   var r = LengthDescriber.describe_hours(1.5);
   equals(r, "1 hour 30 minutes");
   var r = LengthDescriber.describe_hours(2.5);
   equals(r, "2 hours 30 minutes");
   var r = LengthDescriber.describe_hours(1.75);
   equals(r, "1 hour 45 minutes");
   var r = LengthDescriber.describe_hours(0.2);
   equals(r, "12 minutes");
});

test("LengthDescriber, days", function() {
   var r = LengthDescriber.describe_days(1);
   equals(r, "All day");
   var r = LengthDescriber.describe_days(2);
   equals(r, "2 days");
});

test("Test utils.ordinalize()", function() {
   equals(utils.ordinalize(1), "1st");
   equals(utils.ordinalize(2), "2nd");
   equals(utils.ordinalize(3), "3rd");
   equals(utils.ordinalize(4), "4th");
   equals(utils.ordinalize(11), "11th");
   equals(utils.ordinalize(12), "12th");
   equals(utils.ordinalize(13), "13th");
   equals(utils.ordinalize(14), "14th");
   equals(utils.ordinalize(21), "21st");
   equals(utils.ordinalize(22), "22nd");
   equals(utils.ordinalize(23), "23rd");
   equals(utils.ordinalize(24), "24th");
   equals(utils.ordinalize(46114), "46114th");
});

test("Test utils.month_name()", function() {
  equals(utils.month_name(1), "January");
  equals(utils.month_name(12), "December");
});

test("format_hour", function() {
  //not yet
});

module("Storage and AJAX", {
   setup: function() {
      localStorage.clear();
   },
   teardown: function() {
      localStorage.clear();
   }
});

test("Storing things", function() {
   ok(typeof(localStorage) != 'undefined');
   ok(JSON);

   equals(Store.get('notyet'), null);

   Store.set('info', {name:"Peter"});
   equals(Store.get('info').name, "Peter");

   Store.update('key1', {age:31});
   Store.update('key2', {foo:'bar'});

   equals(JSON.parse(localStorage.getItem('key1')).age, 31);
   var _keys = JSON.parse(localStorage.getItem('store_keys'));
   equal(_keys.length, 2);
   equal(_keys[0], 'key2');
   equal(_keys[1], 'key1');

   Store.remove('info');
   ok(!localStorage.getItem('info'));
   var _keys = JSON.parse(localStorage.getItem('store_keys'));
   equal(_keys.length, 2);
   equal(_keys[0], 'key2');
   equal(_keys[1], 'key1');

   Store.remove('key1');
   ok(!localStorage.getItem('key1'));
   var _keys = JSON.parse(localStorage.getItem('store_keys'));
   equal(_keys.length, 1);
   equal(_keys[0], 'key2');

   // test the default thing
   equals(Store.get('xxx', 0), 0);
   equals(Store.get('xxx', false), false);
   equals(Store.get('xxx', 'peter'), 'peter');

   Store.clear();
   ok(!localStorage.getItem('key2'));
});

test("Storing objects as JSON", function() {
   Store.set('string', 'String');
   equals(Store.get('string'), 'String');
   Store.set('number', 123);
   equals(Store.get('number'), 123);

   Store.set('like number', '1001');
   equals(Store.get('like number'), '1001');

   Store.set('array', ['one', 'two']);
   equals(Store.get('array').length, 2);
   equals(Store.get('array')[0], 'one');
   equals(Store.get('array')[1], 'two');
});

var MockMobile = function() {
   this.current_page;
};
MockMobile.prototype.changePage = function(location) {
   this.current_page = location;
};

test("test Auth", function() {
   $.mobile = new MockMobile();
   var _last_alert;
   alert = function(msg) {
      _last_alert = msg;
   };
   $.ajax = function(options) {
      switch (options.url) {
       case '/smartphone/checkguid/':
	 options.success({ok:true});
	 break;
       case '/smartphone/auth/login/':
	 if (options.data.password == 'secret')
	   options.success({guid:'10001'});
	 else
	   options.success({error:"Wrong credentials"});
	 break;
       default:
	 console.log(options.url);
	 throw new Error("Mock not prepared (" + options.url + ")");
      }
   };
   var result = Auth.is_logged_in(false);
   equals(result, false);

   Auth.ajax_login('peterbe@example.com', 'other junk');
   ok(_last_alert);
   //equals($.mobile.current_page.selector, '#start');
   equals(Store.get('guid'), null);

   Auth.ajax_login('peterbe@example.com', 'secret');
   equals($.mobile.current_page.selector, '#start');
   equals(Store.get('guid'), '10001');



});
