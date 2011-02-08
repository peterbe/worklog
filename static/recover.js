head.ready(function() {
   head.js(JS_URLS.validate, function() {
      var validated_emails = {};

      $('form.recover').validate({
         rules: {
            password: {
               required: true,
               minlength: 4
            }
         }
      });
   });

   $('input[name="password"]').focus();
});
