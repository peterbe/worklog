function L() {
   console.log.apply(console, arguments);
}
$(document).bind("mobileinit", function () {
   $.extend($.mobile, { ajaxFormsEnabled: false });
});



$(document).ready(function() {
   $('#login form').submit(function() {
      if (!$('input[name="email"]', this).val()) {
         return false;
      }
      if (!$('input[name="password"]', this).val()) {
         return false;
      }
      //L($('input[name="email"]', this)); 
      //L($('input[name="password"]', this));
      //return false;
      return true;
   });
});