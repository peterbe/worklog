$(function() {
   $.getScript(JS_URLS.validate, function() {
      var validated_emails = {};
      
      $('form.forgotten').validate({
         rules: {
            email: {
               required: true,
               email: true
            }
         },
         onkeyup: false
      });
   });
   
   $('input[name="email"]').focus();
});

