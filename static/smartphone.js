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
   return {
      create_calendar: function() {
         L("create_calendar()");
         $('#calendar').fullCalendar({
            editable: true,
            events: function(start, end, callback) {
               var url = '/api/events.json';//?guid=" + authentication.get_guid();
               var ops = {
                  start: start.getTime(), 
                  end: end.getTime(),
                  guid: authentication.get_guid()
               };
               $.getJSON(url, ops, function(response) {
                  callback(response.events);
               });
            },
            defaultView: 'month'
            //      timeFormat: SETTINGS.ampm_format ? 'h(:mm)tt' : 'H:mm'
            //loading: function(bool) {
            //   if (bool) $('#loading').show();
            //   else $('#loading').hide();
            //}
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
   //$('#start').bind('pageshow', function() {
   //   L('start pageshow');
   //});
});