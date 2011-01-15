function L() {
   console.log.apply(console, arguments);
}
$(document).bind("mobileinit", function () {
   //$.extend($.mobile, { ajaxFormsEnabled: false });
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
      }
   }
})();

var authentication = (function() {
   //$.storage = new $.store();
   //var guid = localStorage.getItem('guid');
   var login_initialized=false;

   return {
      get_guid: function() {
         return localStorage.getItem('guid');;
      },
      set_guid: function(guid) {
         alert("Setting guid:" + guid);
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
            L("is logged in");
	    return true;
	 }
         L("not logged in");
         return false;
      },

      redirect_login: function() {
         L("redirect_login()");
         if (!login_initialized) {
            authentication.init_login();
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
                  alert(response);
               } else if (response.guid) {
                  authentication.set_guid(response.guid);
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



var calendar = (function() {
   var months_loaded = null;

   return {
      set_current_year: function(year) {
         localStorage.setItem('current_year', year);
      },
      get_current_year: function(year) {
         localStorage.getItem('current_year');
      },
      set_current_month: function(month) {
         localStorage.setItem('current_month', month);
      },
      get_current_month: function(month) {
         localStorage.getItem('current_month');
      },
      set_current_day: function(day) {
         localStorage.setItem('current_day', day);
      },
      get_current_day: function(day) {
         localStorage.getItem('current_day');
      },
      init_months: function() {
         if (months_loaded === null) {
            this.load_months();
            months_loaded = {};
         }
      },
      init_month: function(year, month) {
         this.set_current_year(year);
         this.set_current_month(month);
         var key = year + '-' + month;
         L("init_month()", key, months_loaded[key]===undefined);

         if (undefined === months_loaded[key]) {
            this.load_month(year, month);
         }
      },
      load_month: function(year, month) {
         L("load_month()");
         $('#calendar-month-days li').remove();
         $('#calendar-month h1').text(utils.month_name(month) + ', ' + year);
	 var self = this;
         $.getJSON('/smartphone/api/month.json',
                   {guid:authentication.get_guid(), year:year, month:month},
                   function(response) {
                      var container = $('#calendar-month-days');
                      $.each(response.day_counts, function(i, e) {
                         var inner_container = $('<li>').appendTo(container);
                         $('<a>', {text:i + 1, href:'#calendar-day'})
                           .click(function() {
                              self.init_day(year, month, i + 1);
                           })
			   .appendTo(inner_container);
                         $('<span>', {text:e})
                           .addClass('ui-li-count')
                             .appendTo(inner_container);
                      });
		      $('#calendar-month-days').listview('refresh');
                   });
      },
      load_months: function() {
         L("loading_months()");
         var self = this;
	 $.getJSON('/smartphone/api/months.json', {guid:authentication.get_guid()} ,
		   function(response) {
		      var container = $('#calendar-months');
		      $.grep(response.months, function(e, i) {
                         var inner_container = $('<li>').appendTo(container);
                         var text = utils.month_name(e.month) + ', ' + e.year;
			 $('<a>', {text:text, href:'#calendar-month'})
                           .click(function() {
                              self.init_month(e.year, e.month);
                           })
			   .appendTo(inner_container);
                         $('<span>', {text:e.count})
                           .addClass('ui-li-count')
                             .appendTo(inner_container);

		      });

		      $('#calendar-months').listview('refresh');
		   });
      },
      init_day: function(year, month, day) {
         this.set_current_year(year);
         this.set_current_month(month);
         this.set_current_day(day);
	 var self = this;
         $('#calendar-day-events li').remove();
         $('#calendar-day h1').text(utils.ordinalize(day) + ' ' + utils.month_name(month) + ', ' + year);
	 $.getJSON('/smartphone/api/day.json',
		   {guid:authentication.get_guid(), year:year, month:month, day:day},
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
		   });
      }
   }

})();

$(document).ready(function() {
   $('#start').bind('pagecreate', function() {
      if (!authentication.is_logged_in(true)) {
         L("active page", $.mobile.activePage);
         authentication.redirect_login();
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

         authentication.ajax_login($('input[name="email"]', this).val(),
                                   $('input[name="password"]', this).val());
         return false;
      });

   });

   $('#calendar-page').bind('pageshow', function() {
      calendar.create_calendar();
   });

   $('#logout').bind('pageshow', function() {
      L("pageshow logout");
      authentication.logout();
   });

   $('#calendar').bind('pageshow', function() {
      L("pageshow calendar");
      calendar.init_months();
   });

   //$('#start').bind('pageshow', function() {
   //   L('start pageshow');
   //});
});