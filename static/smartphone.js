function L() {
   console.log.apply(console, arguments);
}
$(document).bind("mobileinit", function () {
   //$.extend($.mobile, { ajaxFormsEnabled: false });
});


var authentication = (function() {
   var guid;
   var login_initialized=false;
   
   return {
      is_logged_in: function() {
         return false;
      },
      
      redirect_login: function() {
         if (!login_initialized) {
            authentication.init_login();
         }
         $.mobile.changePage($('#login'), 'pop');
      },
      
      ajax_login: function(email, password) {
         $.post('auth/login/', {email:email, password:password}, function(response) {
            if (response.toLowerCase().substring(0, 5) == 'error') {
               alert(response);
            } else if (response.length) {
               this.store_guid(response);
            }
         });
      },
      store_guid: function(guid) {
         
      },
      init_login: function() {
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
         login_initialized = true;
      }
   }
})();


$(document).ready(function() {
   $('#start').bind('pagecreate', function() {
      L('start pagecreate');
      L($.mobile.activePage);
      if (!authentication.is_logged_in()) {
         authentication.redirect_login();
      }
   });
   //$('#start').bind('pageshow', function() {
   //   L('start pageshow');
   //});
});