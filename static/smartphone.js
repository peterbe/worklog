function L() {
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
         settings = localStorage.getItem('settings');//$.storage.get('settings');
         L("settings", settings);
      },
      update: function() {

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

var Auth = (function() {
   //$.storage = new $.store();
   //var guid = localStorage.getItem('guid');
   var login_initialized=false;

   return {
      get_guid: function() {
         return localStorage.getItem('guid');;
      },
      set_guid: function(guid) {
         localStorage.setItem('guid', guid);
      },
      unset_guid: function() {
         localStorage.removeItem('guid');
      },
      logout: function() {
         localStorage.clear();
      },
      is_logged_in: function(update_settings) {
	 //if ($.storage.get('guid')) {
         L("is_logged_in()");
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
            //L("is logged in");
	    return true;
	 }
         //L("not logged in");
         return false;
      },

      redirect_login: function() {
         //L("redirect_login()");
         if (!login_initialized) {
            Auth.init_login();
         }
         L("  change to #login");
         // THIS DOESN'T WORK :(
         $.mobile.changePage($('#login'), 'pop', false, false);
      },

      ajax_login: function(email, password) {
         $.ajax({url:'auth/login/?x=y',
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
     , _online;
   //var current_year;

   return {
      set_current_year: function(year) {
	 //current_year=year;
         sessionStorage.setItem('current_year', year);
	 //L("SAT current_year="+year);
      },
      get_current_year: function(year) {
	 //L("Getting current_year");
	 //L("session", sessionStorage.getItem('current_year'));
	 //L("private scope", current_year);
         return sessionStorage.getItem('current_year');
      },
      set_current_month: function(month) {
         sessionStorage.setItem('current_month', month);
      },
      get_current_month: function(month) {
         return sessionStorage.getItem('current_month');
      },
      set_current_day: function(day) {
         sessionStorage.setItem('current_day', day);
      },
      get_current_day: function(day) {
         return sessionStorage.getItem('current_day');
      },
      init_months: function() {
         if (years_loaded && years_loaded.length) {
            // here it might be worth reloading the months
         } else {
            this.load_months();
         }
      },
      init_month: function(year, month) {
         if (months_loaded[year] == undefined || -1 == months_loaded[year].indexOf(month)) {
            this.load_month(year, month);
         } else {
            // consider reloading the month
         }
      },
      load_month: function(year, month) {
         $('#calendar-month-days li').remove();
         $('#calendar-month h1').text(utils.month_name(month) + ', ' + year);
	 var self = this
           , today = new Date()
           , this_month = today.getFullYear() == year && today.getMonth() == month - 1;

         if (months_loaded[year] == undefined) {
            months_loaded[year] = [];
         }


         $.getJSON('/smartphone/api/month.json',
                   {guid:Auth.get_guid(), year:year, month:month},
                   function(response) {
                      var container = $('#calendar-month-days');
                      var first_day = response.first_day;
                      var day_names = ['Monday','Tuesday','Wednesday','Thursday',
                                       'Friday','Saturday','Sunday'];
                      var i2 = day_names.indexOf(first_day);
                      $.each(response.day_counts, function(i, e) {
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
                              //self.init_day(year, month, i + 1);
                           })
			   .appendTo(inner_container);
                         $('<span>', {text:e})
                           .addClass('ui-li-count')
                             .appendTo(inner_container);
                         i2++;
                      });
		      $('#calendar-month-days').listview('refresh');
                      months_loaded[year].push(month);
                   });
      },
      load_months: function() {
         var self = this;
	 $.getJSON('/smartphone/api/months.json', {guid:Auth.get_guid()} ,
		   function(response) {
		      var container = $('#calendar-months');
		      $.grep(response.months, function(e, i) {
                         var inner_container = $('<li>').appendTo(container);
                         var text = utils.month_name(e.month) + ', ' + e.year;
			 $('<a>', {text:text, href:'#calendar-month'})
                           .click(function() {
			      self.set_current_year(e.year);
			      self.set_current_month(e.month);
                              //self.init_month(e.year, e.month);
                           })
			   .appendTo(inner_container);
                         $('<span>', {text:e.count})
                           .addClass('ui-li-count')
                             .appendTo(inner_container);
                         if (-1 == years_loaded.indexOf(e.year)) {
                            years_loaded.push(e.year);
                         }
		      });
		      $('#calendar-months').listview('refresh');
		   });
      },
      init_day: function(year, month, day) {
         if (undefined == days_loaded[year]
             || undefined == days_loaded[year][month]
             || -1 == days_loaded[year][month].indexOf(day)) {
            this.load_day(year, month, day);
         } else {
            // consider reloading the day
         }
      },
      load_day: function(year, month, day) {
         this.set_current_year(year);
         this.set_current_month(month);
         this.set_current_day(day);
	 var self = this;
         $('#calendar-day-events li').remove();
         $('#calendar-day h1').text(utils.ordinalize(day) + ' ' + utils.month_name(month));
         if (undefined == days_loaded[year]) {
            days_loaded[year] = {};
         }
         if (undefined == days_loaded[year][month]) {
            days_loaded[year][month] = [];
         }

	 $.getJSON('/smartphone/api/day.json',
		   {guid:Auth.get_guid(), year:year, month:month, day:day},
		   function(response) {
                      var container = $('#calendar-day-events');
                      $.each(response.events, function(i, e) {
                         var inner_container = $('<li>').appendTo(container);
                         $('<a>', {text:e.title, href:'#calendar-event'})
                           .click(function() {
                              self.init_event(e.id);
                           })
			   .appendTo(inner_container);
                         $('<span>', {text:e.length})
                           .addClass('ui-li-count')
                             .appendTo(inner_container);
                      });
		      $('#calendar-day-events').listview('refresh');
                      $('#calendar-days-totals').html('');
                      if (response.totals) {
                         var container = $('#calendar-days-totals');
                         if (response.totals.days_spents) {
                            //var container = $('<p>').css('text-align', 'right');
                            $('<dt>', {text:'Total days: '}).appendTo(container);
                            $('<dd>', {text:response.totals.days_spent}).appendTo(container);
                            container.appendTo($('#calendar-days-totals'));
                         }
                         if (response.totals.hours_spent) {
                            //var container = $('<p>').css('text-align', 'right');
                            $('<dt>', {text:'Total hours: '}).appendTo(container);
                            $('<dd>', {text:response.totals.hours_spent}).appendTo(container);
                            //container.appendTo($('#calendar-days-totals'));
                         }
                      }
                      days_loaded[year][month].push(day);
		   });
      },
      isOnline: function() {
         _isOnline = true;
      },
      isOffline: function() {
         _online = false;
      }
   }

})();

$(document).ready(function() {
   $('#start').bind('pagecreate', function() {
      if (!Auth.is_logged_in(true)) {
         Auth.redirect_login();
      }
   });

   $('#login').bind('pagecreate', function() {
      L('Creating #login');
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
      L('Showing #login');
   });

   $('#calendar-day').bind('pagecreate', function() {
      $('input[name="duration"]').change(function() {
         if ($(this).val() == 'other') {
            $('#field-duration-other:hidden').show();
         } else {
            $('#field-duration-other:visible').hide();
         }
      });
      var form = $('form', '#calendar-day-add-collapse');
      form.submit(function() {
         if (!$('input[name="title"]', form).val()) {
            alert("Please type something first");
            return false;
         }
         if ($('input[name="duration"]:checked', form).val() == 'other') {
            if (!$('input[name="duration_other"]', form).val()) {
               alert("Please enter the number of hours");
               return false;
            }
         }

         data = {guid:Auth.get_guid(),
            title: $('input[name="title"]', form).val(),
            duration: $('input[name="duration"]:checked', form).val(),
            duration_other: $('input[name="duration_other"]', form).val(),
            year: Calendar.get_current_year(),
            month: Calendar.get_current_month(),
            day: Calendar.get_current_day()
         };

         $.post('/smartphone/api/day.json', data, function(response) {
            if (response.error) {
               alert(response.error);
               return;
            }
            var container = $('#calendar-day-events');
            var inner_container = $('<li>').appendTo(container);
            $('<a>', {text:response.event.title, href:'#calendar-event'})
              .click(function() {
                 self.init_event(response.event.id);
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
   });

   $('#calendar-page').bind('pageshow', function() {
      Calendar.create_calendar();
   });

   $('#logout').bind('pageshow', function() {
      Auth.logout();
   });

   $('#calendar').bind('pageshow', function() {
      L("Showing calendar page", $.mobile.activePage);
      if (Auth.is_logged_in()) {
         Calendar.init_months();
      } else {
         $.mobile.changePage('#login');
      }
   });

   $('#calendar-month').bind('pageshow', function() {
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

   $('#calendar-day').bind('pageshow', function() {
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

   if (window.addEventListener) {
      window.addEventListener("online", Calendar.isOnline, false);
      window.addEventListener("offline", Calendar.isOffline, false);
   } else {
      document.body.ononline = Calendar.isOnline;
      document.body.onoffline = Calendar.isOffline;
   }
});