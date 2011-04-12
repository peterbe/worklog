function L() {
   if (window.console && window.console.log)
     console.log.apply(console, arguments);
}
$(document).bind("mobileinit", function () {
   $.extend($.mobile, { ajaxFormsEnabled: false });

});

var user_settings = (function() {
   //$.storage = new $.store();
   var settings;
   return {
      init : function() {
         settings = Store.get('settings');//$.storage.get('settings');
         L("settings", settings);
      },
      update: function() {

      }
   }
})();

var LengthDescriber = (function() {
   return {
      describe_days: function(days) {
         if (days == 1) {
            return "All day";
         } else {
            return days + " days";
         }
      },
      describe_hours: function(hours) {
	 var minutes = hours * 60;
	 var remainder = minutes % 60;

	 if (hours == 1)
	   return "1 hour";
	 else if (hours < 1)
	   return minutes + " minutes";
	 hours = (minutes - remainder)/60;
	 if (hours == 1)
	   hours += " hour";
	 else
	   hours += " hours";
	 if (remainder)
	   remainder = " " + remainder + " minutes";
	 else
	   remainder = "";
         return hours + remainder;
      }
   }

})();


var MONTH_NAMES = {1:'January', 2:'February', 3:'March', 4:'April', 5:'May', 6:'June',
   7:'July', 8:'August', 9:'September', 10:'October', 11:'November', 12:'December'};

var utils = (function() {
   return {
      ordinalize: function(x) {
	 var n = x % 100;
	 var suff = ["th", "st", "nd", "rd", "th"]; // suff for suffix
	 var ord= n<21?(n<4 ? suff[n]:suff[0]): (n%10>4 ? suff[0] : suff[n%10]);
	 return x + ord;
      },
      month_name: function(x) {
	 return MONTH_NAMES[x];
      },
      format_hour: function(h, ampm_format) {
         if (ampm_format) {
            throw new Error("Haven't done yet");
         } else {
            return h;
         }
      }
   }
})();

var Store = (function() {
   $.storage = new $.store();
   return {
      set: function(key, data) {
	 try {
	    $.storage.set(key, data);
	 } catch(e) {
	    if (e == QUOTA_EXCEEDED_ERR) {
	       alert("Ran out of local storage space.\nWill reset");
	       Store.clear();
	       $.storage.set(key, data);
	    }
	 }
      },
      update: function(key, data) {
	 var keys = $.storage.get('store_keys');
	 keys = keys !== null ? keys: [];
	 if (keys.indexOf(key) > -1) {
	    keys.splice(keys.indexOf(key), 1);
	 }
	 keys.unshift(key);
	 try {
	    $.storage.set('store_keys', keys);
	    $.storage.set(key, data);
	 } catch (e) {
	    if (e == QUOTA_EXCEEDED_ERR) {
	       // need to purge
	       var old_key = keys.pop(); // oldest thing stored
	       Store.remove(old_key);
	       $.storage.set('store_keys', keys);
	       Store.update(key, data); // try again
	    }
	 }
      },
      get: function(key, default_) {
	 var data = $.storage.get(key);
	 default_ = typeof(default_) != 'undefined' ? default_ : null;
	 if (null === data) {
	    data = default_;
	 }
	 return data;
      },
      remove: function(key) {
	 var keys = this.get('store_keys', []);
	 if (keys.indexOf(key) > -1) {
	    keys.splice(keys.indexOf(key), 1);
	    this.set('store_keys', keys);
	 }
	 $.storage.del(key);
      },
      clear: function() {
	 $.storage.flush();
      }
   }
})();

var Auth = (function() {
   var login_initialized = false;

   return {
      get_guid: function() {
	 return Store.get('guid');
      },
      set_guid: function(guid) {
	 Store.set('guid', guid);
      },
      //unset_guid: function() {
      //   Store.del('guid');
      //},
      logout: function() {
         Store.clear();
      },
      is_logged_in: function(update_settings) {
	 //if ($.storage.get('guid')) {
         if (this.get_guid()) {
            if (update_settings) { // also reason to double check the GUID
               $.getJSON('/smartphone/checkguid/', {guid:this.get_guid()}, function(response) {
                  if (response && response.ok) {
                     if (false && update_settings) {
                        $.getJSON('usersettings/', {guid:this.get_guid()}, function(response) {
                           L(response);
                           return;
                           if (!response.ok) {
                              this.unset_guid();
                              //$.storage.del('guid');
                              $.mobile.changePage($('#login'), 'pop');
                              // consider a flash message
                           }
                        });
                     } else {
                        //user_settings.update($.storage.get('guid'));
                     }
                  } else {
                     $.mobile.changePage($('#login'), 'pop');
                  }
               });
            }
	    return true;
	 }
         return false;
      },

      redirect_login: function() {
         if (!login_initialized) {
            Auth.init_login();
         }
         // THIS DOESN'T WORK :( // or does it now???
         $.mobile.changePage($('#login'), 'pop', false, false);
      },

      ajax_login: function(email, password) {
         $.ajax({url:'/smartphone/auth/login/',
            type:'POST',
            dataType:'json',
            data:{email:email, password:password},
            success:function(response) {
               if (response.error) {
                  alert(response.error);
               } else if (response.guid) {
                  Auth.set_guid(response.guid);
                  $.mobile.changePage($('#start'), 'pop');
               }
            }
         });
      },
      init_login: function() {
         login_initialized = true;
      }
   }
})();



var Calendar = (function() {
   var months_loaded = {}
     , years_loaded = []
     , days_loaded = {}
     , events_loaded = {}
     , last_day_loaded
     , last_month_loaded
     , last_event_loaded
     , _online = true; // assume so


   /* fetch only the latest timestamp (quick) and if newer than what we
    currently have then reload the month. */
   function check_and_reload_month(year, month, storage_key) {
      $.getJSON('/smartphone/api/month.json',
		{guid:Auth.get_guid(), year:year, month:month, timestamp_only:true},
		function(response) {
		   if (response.timestamp) {
		      if (response.timestamp > Store.get('timestamps', {})[storage_key]) {
			 // there is more fresh content for this
			 Store.remove(storage_key);
			 Calendar.load_month(year, month, storage_key);
		      }
		   }
		});
   }

   function check_and_reload_years(storage_key) {
      $.getJSON('/smartphone/api/months.json',
		{guid:Auth.get_guid(), timestamp_only:true} ,
		function(response) {
		   if (response.timestamp > Store.get('timestamps')[storage_key]) {
		      Store.remove(storage_key);
		      Calendar.load_months(storage_key); // reload
		   }
		});
   }
   function check_and_reload_day(year, month, day, storage_key) {
      $.getJSON('/smartphone/api/day.json',
                {guid:Auth.get_guid(), year:year, month:month, day:day, timestamp_only:true},
                function(response) {
                   if (response.error) {
                      alert(response.error);
                   } else {
		      if (response.timestamp > Store.get('timestamps', {})[storage_key]) {
			 // there is more fresh content for this
			 Store.remove(storage_key);
			 Calendar.load_day(year, month, day, storage_key);
		      }

                   }
                });

   }

   function check_and_reload_event(event_id, storage_key) {
      $.getJSON('/smartphone/api/event.json',
                {guid:Auth.get_guid(), id:event_id, timestamp_only:true},
                function(response) {
                   if (response.error) {
                      alert(response.error);
                   } else {
		      if (response.timestamp > Store.get('timestamps', {})[storage_key]) {
			 // there is more fresh content for this
			 Store.remove(storage_key);
			 Calendar.load_event(event_id, storage_key);
		      }
                   }
                });
   }

   return {
      clear_last_day_loaded: function() {
         last_day_loaded = null;
      },
      set_current_year: function(year) {
         sessionStorage.setItem('current_year', year);
      },
      get_current_year: function() {
         return sessionStorage.getItem('current_year');
      },
      set_current_month: function(month) {
         sessionStorage.setItem('current_month', month);
      },
      get_current_month: function() {
         return sessionStorage.getItem('current_month');
      },
      set_current_day: function(day) {
         sessionStorage.setItem('current_day', day);
      },
      get_current_day: function() {
         return sessionStorage.getItem('current_day');
      },
      set_current_event_id: function(event_id) {
         sessionStorage.setItem('current_event_id', event_id);
      },
      get_current_event_id: function() {
         return sessionStorage.getItem('current_event_id');
      },
      init_months: function() {
	 var storage_key = 'years';
         if (years_loaded.length) { // remember, empty arrays are true
            // here it might be worth reloading the months
	    if (Calendar.isOnline()) {
	       check_and_reload_years(storage_key);
	    }
         } else {
            this.load_months(storage_key);
         }
      },
      load_months: function(storage_key) {
	 if(typeof(storage_key)=='undefined') throw new Error("Poop"); // ????
         var self = this;
         $('#calendar-months li').remove();
	 function _display_data(data) {
	    var container = $('#calendar-months');
	    $.grep(data.months, function(e, i) {
	       var inner_container = $('<li>').appendTo(container);
	       var text = utils.month_name(e.month) + ', ' + e.year;
	       $('<a>', {text:text, href:'#calendar-month'})
		 .click(function() {
		    self.set_current_year(e.year);
		    self.set_current_month(e.month);
		 })
		   .appendTo(inner_container);
	       $('<span>', {text:e.count})
		 .addClass('ui-li-count')
		   .appendTo(inner_container);
	       if (-1 == years_loaded.indexOf(e.year)) {
		  years_loaded.push(e.year);
	       }
	    });
            try {
               $('#calendar-months').listview('refresh');
            } catch(e) {
               L("ERROR", e);
            }
	 }
	 var stored_data = Store.get(storage_key);
	 if (!stored_data){
	    $.getJSON('/smartphone/api/months.json', {guid:Auth.get_guid()} ,
		   function(response) {
                      if (response.error) {
                         alert(response.error);
                      } else {
                         _display_data(response);
                         var timestamps = Store.get('timestamps', {});
                         timestamps[storage_key] = response.timestamp;
                         Store.set('timestamps', timestamps);
                         Store.update(storage_key, response);
                      }
		   });
	 } else {
	    _display_data(stored_data);
	    if (Calendar.isOnline()) {
	       check_and_reload_years(storage_key);
	    }
	 }
      },
      init_month: function(year, month) {
	 var storage_key = '' + year + month;
         if (storage_key != last_month_loaded) {
            this.load_month(year, month, storage_key);
         } else {
            if (Calendar.isOnline()) {
	       check_and_reload_month(year, month, storage_key);
            }
         }
      },

      load_month: function(year, month, storage_key) {
         $('#calendar-month h1').text(utils.month_name(month) + ', ' + year);
         $('#calendar-month-days li').remove();
	 var self = this
           , today = new Date()
           , this_month = today.getFullYear() == year && today.getMonth() == month - 1;

	 function _display_data(data) {
	    var container = $('#calendar-month-days');
	    var first_day = data.first_day;
	    var day_names = ['Monday','Tuesday','Wednesday','Thursday',
			     'Friday','Saturday','Sunday'];
	    var i2 = day_names.indexOf(first_day);
	    $.each(data.day_counts, function(i, e) {
	       var inner_container = $('<li>').appendTo(container);
	       var text = i + 1;
	       if (this_month) {
		  if (i + 1 == today.getDate()) {
		     text += ' Today';
		  }
	       }
	       i2 = i2 % 7;
	       //text += ' ' + day_names[i2];
	       $('<a>', {href:'#calendar-day'})
		 .append($('<span>', {text:text}))
		   .append($('<span>', {text:day_names[i2]})
			   .addClass('dayname')
			   .addClass('dayname_' + (i2+1)))
		     .click(function() {
			self.set_current_day(i + 1);
		     })
		       .appendTo(inner_container);
	       $('<span>', {text:e})
		 .addClass('ui-li-count')
		   .appendTo(inner_container);
	       i2++;
	    });
	    $('#calendar-month-days').listview('refresh');
            last_month_loaded = storage_key;
	 }

	 var stored_data = Store.get(storage_key);
	 if (!stored_data) {
	    $.getJSON('/smartphone/api/month.json',
		      {guid:Auth.get_guid(), year:year, month:month},
		      function(response) {
			 if (response.error) {
			    alert(response.error);
			 } else {
			    _display_data(response);
                            var timestamps = Store.get('timestamps', {});
                            timestamps[storage_key] = response.timestamp;
			    Store.set('timestamps', timestamps);
			    Store.update(storage_key, response);
			 }
		      });
	 } else {
	    // yay! we can use local storage
	    _display_data(stored_data);
	    // if we're online, check if the latest timestamp has been updated
            if (Calendar.isOnline()) {
	       check_and_reload_month(year, month, storage_key);
            }
	 }
      },
      init_day: function(year, month, day) {
	 var storage_key = '' + year + month + day;
         if (storage_key != last_day_loaded) {
            this.load_day(year, month, day, storage_key);
         } else {
            if (Calendar.isOnline()) {
	       check_and_reload_day(year, month, day, storage_key);
            }
         }
      },
      load_day: function(year, month, day, storage_key) {
         this.set_current_year(year);
         this.set_current_month(month);
         this.set_current_day(day);
	 var self = this;
         $('#calendar-day h1').text(utils.ordinalize(day) + ' ' + utils.month_name(month));
         $('#calendar-day-events li').remove();

	 function _display_data(data) {
	    var container = $('#calendar-day-events')
              , days_spent = 0
              , hours_spent = 0.0
              , length;
	    $.each(data.events, function(i, e) {
	       var inner_container = $('<li>').appendTo(container);
	       $('<a>', {text:e.title, href:'#calendar-event'})
		 .click(function() {
                    self.set_current_event_id(e.id);
		 })
		   .appendTo(inner_container);

               if (e.all_day) {
                  length = LengthDescriber.describe_days(e.days);
               } else {
                  length = LengthDescriber.describe_hours(e.hours);
               }
	       $('<span>', {text:length})
		 .addClass('ui-li-count')
		   .appendTo(inner_container);
               if (e.all_day)
                 days_spent += e.days;
               else
                 hours_spent += e.hours;
	    });
	    $('#calendar-day-events').listview('refresh');
	    $('#calendar-days-totals').html('');
	    if (days_spent || hours_spent) {
	       var container = $('#calendar-days-totals');
	       if (days_spent) {
		  $('<dt>', {text:'Total days: '}).appendTo(container);
		  $('<dd>', {text:days_spent}).appendTo(container);
	       }
	       if (hours_spent) {
		  $('<dt>', {text:'Total hours: '}).appendTo(container);
		  $('<dd>', {text:hours_spent}).appendTo(container);
	       }
	    }
	    last_day_loaded = storage_key;
	 }

	 var stored_data = Store.get(storage_key);
	 if (!stored_data) {
	    $.getJSON('/smartphone/api/day.json',
		   {guid:Auth.get_guid(), year:year, month:month, day:day},
		   function(response) {
			 if (response.error) {
			    alert(response.error);
			 } else {
			    _display_data(response);
                            var timestamps = Store.get('timestamps', {});
                            timestamps[storage_key] = response.timestamp;
			    Store.set('timestamps', timestamps);
			    Store.update(storage_key, response);
			 }
		   });
	 } else {
	    // yay! we can use local storage
	    _display_data(stored_data);
	    // if we're online, check if the latest timestamp has been updated
            if (Calendar.isOnline()) {
	       check_and_reload_day(year, month, day, storage_key);
            }
	 }
      },
      init_event: function(event_id) {
         var storage_key = '' + event_id;
         if (storage_key != last_event_loaded) {
            this.load_event(event_id, storage_key);
         } else {
            if (Calendar.isOnline()) {
	       check_and_reload_event(event_id, storage_key);
            }
         }
      },
      load_event: function(event_id, storage_key) {
         this.set_current_event_id(event_id); // excessive?
         var day = this.get_current_day();
         var month = this.get_current_month();
         $('#calendar-event h1').text(utils.ordinalize(day) + ' ' + utils.month_name(month));
	 var self = this;
         function _display_data(data) {
            $('input[name="title"]', '#calendar-event').val(data.event.title);
            if (data.event.description) {
               $('textarea[name="description"]', '#calendar-event').val(data.event.description);
            }
            if (data.event.days) {
               $('#field-duration-days:hidden').show();
               $('#field-duration-hours:visible').hide();
               $('input[name="duration_days"]', '#field-duration-days').val(data.event.days);
            } else {
               $('#field-duration-hours:hidden').show();
               $('#field-duration-days:visible').hide();
               $('input[name="duration_hours"]', '#field-duration-hours').val(data.event.hours);
            }
            last_event_loaded = storage_key;
         }
	 var stored_data = Store.get(storage_key);
	 if (!stored_data) {
	    $.getJSON('/smartphone/api/event.json',
                      {guid:Auth.get_guid(), id:event_id},
                      function(response) {
                         if (response.error) {
                            alert(response.error);
                         } else {
                            _display_data(response);
                            var timestamps = Store.get('timestamps', {});
                            timestamps[storage_key] = response.timestamp;
			    Store.set('timestamps', timestamps);
			    Store.update(storage_key, response);
                         }
                      });
         } else {
            _display_data(stored_data);
            if (Calendar.isOnline()) {
	       check_and_reload_event(event_id, storage_key);
            }
         }
      },
      isOnline: function() {
         return _online;
      },
      isOffline: function() {
         return !Calendar.isOnline();
      },
      setOnline: function() {
         _online = true;
      },
      setOffline: function() {
         _online = false;
      }
   }

})();

$(document).ready(function() {
   if (location.hash && location.hash.search(/^#guid-/) > -1) {
      Auth.set_guid(location.hash.split('#guid-')[1]);
      location.hash = '#start';
   }

   $('#start').bind('pagecreate', function() {
      if (!Auth.is_logged_in(true)) {
         Auth.redirect_login();
      }
   });

   $('#login').bind('pagecreate', function() {
      $('#login form').submit(function() {
         if (!$('input[name="email"]', this).val()) {
            return false;
         }
         if (!$('input[name="password"]', this).val()) {
            return false;
         }

         Auth.ajax_login($('input[name="email"]', this).val(),
                         $('input[name="password"]', this).val());
         return false;
      });
   });

   $('#login').bind('pageshow', function() {
   });

   $('#calendar-day').bind('pagecreate', function() {
      $('input[name="duration"]').change(function() {
         if ($(this).val() == 'other') {
            $('#field-duration-other:hidden').show();
         } else {
            $('#field-duration-other:visible').hide();
         }
      });

      $('button.cancel', '#calendar-day-add-collapse').click(function() {
	 $('input[name="title"]', form).val('');
	 $('#calendar-day-add-collapse').trigger('collapse');
	 return false;
      });
      $('form', '#calendar-day-add-collapse').submit(function() {
         if (!$('input[name="title"]', this).val()) {
            alert("Please type something first");
            return false;
         }
         if ($('input[name="duration"]:checked', this).val() == 'other') {
            if (!$('input[name="duration_other"]', this).val()) {
               alert("Please enter the number of hours");
               return false;
            }
         }

         var post_data = {guid:Auth.get_guid(),
            title: $('input[name="title"]', this).val(),
            duration: $('input[name="duration"]:checked', this).val(),
            duration_other: $('input[name="duration_other"]', this).val(),
            year: Calendar.get_current_year(),
            month: Calendar.get_current_month(),
            day: Calendar.get_current_day()
         };

	 var form = this;
         $.post('/smartphone/api/day.json', post_data, function(response) {
            if (response.error) {
               alert(response.error);
               return;
            }
            var container = $('#calendar-day-events');
            var inner_container = $('<li>').appendTo(container);
            $('<a>', {text:response.event.title, href:'#calendar-event'})
              .click(function() {
		 // could potentiall copy response.event.title to '#calendar-event h3' immediately
                 Calendar.init_event(response.event.id);
              })
                .appendTo(inner_container);
            $('<span>', {text:response.event.length})
              .addClass('ui-li-count')
                .appendTo(inner_container);
            $('#calendar-day-events').listview('refresh');
            $('input[name="title"]', form).val('');
            $('#calendar-day-add-collapse').trigger('collapse');
            //alert("awesome!");

         });
         return false;
      });
   });

   $('#calendar-page').bind('pageshow', function() {
      Calendar.create_calendar();
   });

   $('#logout').bind('pageshow', function() {
      Auth.logout();
   });

   $('#calendar').bind('pageshow', function() {
      if (Auth.is_logged_in()) {
         Calendar.init_months();
      } else {
         $.mobile.changePage('#login');
      }
   });

   $('#calendar-month').bind('pageshow', function() {
      L("IN pageshow for #calendar-month");
      var year = Calendar.get_current_year();
      var month = Calendar.get_current_month();
      if (year && month) {
	 Calendar.init_month(year, month);
      } else {
         if (Auth.is_logged_in()) {
            $.mobile.changePage($('#calendar'));
         } else {
            $.mobile.changePage($('#login'));
         }
      }
   });

   $('#add2today').click(function() {
      var today = new Date();
      Calendar.set_current_year(today.getFullYear());
      Calendar.set_current_month(today.getMonth() + 1);
      Calendar.set_current_day(today.getDate());

      setTimeout(function() {
	 $('#calendar-day-add-collapse', '#calendar-day').trigger('expand');
	 $('input[name="title"]', '#calendar-day').trigger('focus');
      }, 500);
      return true;
   });


   $('#calendar-day').bind('pageshow', function() {
      var container = $('#select-choice-hour');
      var current_hour = new Date().getHours();
      for (var i=0, len=24; i < len; i++) {
         var o = $('<option>', {text:utils.format_hour(i, false)}).val(i);
         if (i == current_hour) {
            o.attr('selected','selected');
         }
         o.appendTo(container);
      }
      $('#select-choice-hour').selectmenu('refresh', true);

      var year = Calendar.get_current_year();
      var month = Calendar.get_current_month();
      var day = Calendar.get_current_day();
      if (year && month && day) {
	 Calendar.init_day(year, month, day);
      } else {
         if (Auth.is_logged_in()) {
            $.mobile.changePage($('#calendar'));
         } else {
            $.mobile.changePage($('#login'));
         }
      }
   });


   $('#calendar-event').bind('pageshow', function() {
      var event_id = Calendar.get_current_event_id();
      if (event_id) {
	 Calendar.init_event(event_id);
      } else {
         if (Auth.is_logged_in()) {
            $.mobile.changePage($('#calendar'));
         } else {
            $.mobile.changePage($('#login'));
         }
      }
   }).bind('pagecreate', function() {
      $('form', '#calendar-event').submit(function() {
         if (!$('input[name="title"]', this).val()) {
            alert("Please enter a title");
            return false;
         }
	 if (!$('input.duration:visible').val()) {
            alert("Please enter the duration");
            return false;
	 }

         var post_data = {guid:Auth.get_guid(),
	    id: Calendar.get_current_event_id(), // perhaps better to use a hidden input
            title: $('input[name="title"]', this).val(),
            duration: $('input.duration:visible', this).val(),
	    description: $('textarea[name="description"]', this).val(),
            external_url: $('input[name="external_url"]', this).val(),
         };

	 var self = this;
         $.post('/smartphone/api/event.json', post_data, function(response) {
            if (response.error) {
               alert(response.error);
               return;
            }
	    var storage_key = Calendar.get_current_event_id();
            var stored_data = Store.get(storage_key);
            if (!stored_data) {
               stored_data = {};
               stored_data.event = {};
            }
            stored_data.timestamp = response.timestamp;
            stored_data.event.title = response.event.title;
            stored_data.event.description = response.event.description;
            stored_data.event.external_url = response.event.external_url;
            stored_data.event.all_day = response.event.all_day;
            if (response.event.all_day)
              stored_data.event.days = response.event.days;
            else
              stored_data.event.hours = response.event.hours;
            Store.set(storage_key, stored_data);

	    storage_key = '' + Calendar.get_current_year() +
	      Calendar.get_current_month() + Calendar.get_current_day();
            stored_data = Store.get(storage_key);
            if (!stored_data) {
               stored_data = {};
               stored_data.events = [];
               stored_data.totals = {}
            }
            stored_data.timestamp = response.timestamp;
            $.each(stored_data.events, function(i, event) {
               if (event.id == response.event.id) {
                  event.title = response.event.title;
                  event.description = response.event.description;
                  event.external_url = response.event.external_url;
                  if (response.event.all_day)
                    event.days = response.event.days;
                  else
                    event.hours = response.event.hours;
                  stored_data.events[i] = event;
               }
            });
            Store.set(storage_key, stored_data);
            Calendar.clear_last_day_loaded();
	    $.mobile.changePage($('#calendar-day'));
	 });
         // stop assuming the calendar-day doesn't need to be re-rendered
	 return false;
      });

      $('button.cancel', this).click(function() {
	 $.mobile.changePage($('#calendar-day'));
	 return false;
      });
   });

   if (window.addEventListener) {
      window.addEventListener("online", Calendar.setOnline, false);
      window.addEventListener("offline", Calendar.setOffline, false);
   } else {
      document.body.ononline = Calendar.setOnline;
      document.body.onoffline = Calendar.setOffline;
   }
});