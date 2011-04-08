var ajax_calls = []
  , month_fixture
  , months_fixture
;

$.ajax = function(options) {
      ajax_calls.push(options);
      switch (options.url) {
       case '/smartphone/api/months.json':
	 options.success(months_fixture);
	 break;
       case '/smartphone/api/month.json':
	 options.success(month_fixture);
	 break;
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

var MockMobile = function() {
   this.current_page;
   this.loading = false;
   this.urlHistory = {'stack':[]};
};
MockMobile.prototype.changePage = function(location) {
   this.current_page = location;
   this.loading = false;
};
MockMobile.prototype.pageLoading = function(b) {
   this.loading = b;
};

$.mobile = new MockMobile();


test("LengthDescriber, hours", function() {
   var r = LengthDescriber.describe_hours(1);
   equals(r, "1 hour");
   r = LengthDescriber.describe_hours(1.5);
   equals(r, "1 hour 30 minutes");
   r = LengthDescriber.describe_hours(2.5);
   equals(r, "2 hours 30 minutes");
   r = LengthDescriber.describe_hours(1.75);
   equals(r, "1 hour 45 minutes");
   r = LengthDescriber.describe_hours(0.2);
   equals(r, "12 minutes");
   r = LengthDescriber.describe_hours(2.0);
   equals(r, "2 hours");
});

test("LengthDescriber, days", function() {
   var r = LengthDescriber.describe_days(1);
   equals(r, "All day");
   r = LengthDescriber.describe_days(2);
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


test("Auth", function() {
   var _last_alert;
   alert = function(msg) {
      _last_alert = msg;
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

   result = Auth.is_logged_in(false);
   equals(result, true);

   result = Auth.is_logged_in(true);
   equals(result, true);

   Auth.redirect_login();
   Store.clear();
   equals($.mobile.current_page.selector, '#login');

});


module("Calendar", {
   setup: function() {
      localStorage.clear();
      // Note: we're not allowed to call sessionStorage.clear()
      // because it causes a security error

      // initialize all listviews
      // this is necessary since otherwise you can get errors about
      // listsviews not being initialized before calling the refresh method.
      $('ul[data-role="listview"]').listview();

      sessionStorage.removeItem('current_year');
      sessionStorage.removeItem('current_month');
      sessionStorage.removeItem('current_day');
      sessionStorage.removeItem('current_event_id');

   },
   teardown: function() {
      localStorage.clear();

      sessionStorage.removeItem('current_year');
      sessionStorage.removeItem('current_month');
      sessionStorage.removeItem('current_day');
      sessionStorage.removeItem('current_event_id');
   }
});

test("loading months", function() {
   ajax_calls = []; // reset
   months_fixture = {
      timestamp: 1300195846,
      months: [{"count": 4, "month_name": "October", "month": 10, "year": 2010},
	       {count: 132, month_name: "November", month: 11, year: 2010}]
   };

   Auth.ajax_login('peterbe@example.com', 'secret');
   equals(Store.get('guid'), '10001');

   Calendar.init_months();
   equals(ajax_calls.length, 2);

   equals($('#calendar-months li').size(), 2);
   equals(Store.get('timestamps').years, 1300195846);
   var years_stored_data = Store.get('years');
   equals(years_stored_data.months.length, 2);
   equals(years_stored_data.months[0].count, 4);
   equals(years_stored_data.months[0].month, 10);
   equals(years_stored_data.months[0].year, 2010);
   equals(years_stored_data.months[0].month_name, "October");
   equals(years_stored_data.months[1].count, 132);
   equals(years_stored_data.months[1].month, 11);
   equals(years_stored_data.months[1].year, 2010);
   equals(years_stored_data.months[1].month_name, "November");

   // calling it a second time should do an AJAX command again but this
   // time to just get the timestamp
   Calendar.init_months();
   equals(ajax_calls.length, 3);
   ok(ajax_calls[2].data.timestamp_only);

   // now pretend the fixture has become different
   months_fixture.timestamp += 1;
   months_fixture.months.push({count:132, month_name:"November", month:12, year:2010});
   Calendar.init_months();
   equals(ajax_calls.length, 5);
   ok(ajax_calls[3].data.timestamp_only);
   ok(!ajax_calls[4].data.timestamp_only);

   equals($('#calendar-months li').size(), 3);
   equals(Store.get('timestamps').years, 1300195846 + 1);
});


test("loading month", function() {
   ajax_calls = []; // reset
   month_fixture = {
      timestamp: 1300456142,
      month_name: "March",
      first_day: "Tuesday",
      day_counts: [1, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
		   0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
   };
   equals(ajax_calls.length, 0); // paranoia on the test setup
   Auth.ajax_login('peterbe@example.com', 'secret');
   equals(ajax_calls.length, 1);

   equals(Store.get('guid'), '10001');
   Calendar.set_current_year(''+2011);
   Calendar.set_current_month(3);
   //$('#calendar-month').trigger('pageshow'); // WHY! doesn't this trigger?!?! ...sometimes
   Calendar.init_month(2011, 3);
   equals(ajax_calls.length, 2);

   equals($('#calendar-month li').size(), month_fixture.day_counts.length);
   equals(Store.get('timestamps')['' + 2011 + 3], month_fixture.timestamp);
   var stored_data = Store.get('' + 2011 + 3);
   equals(stored_data.timestamp, month_fixture.timestamp);
   // can't compare arrays
   equals(stored_data.day_counts.length, month_fixture.day_counts.length);
   equals(stored_data.month_name, 'March');

});
