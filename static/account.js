/* this is loaded automatically when the account page is shown */

var f = $('form.login');
var e = $('input[name="email"]', f);
/*
if (!e.val())
e.val($('input[name="placeholdervalue"]', f).val())
    .addClass('placeholdervalue');
e.bind('focus', function() {
   if ($(this).val() == $('input[name="placeholdervalue"]', f).val())
     $(this).val('').removeClass('placeholdervalue');
}).bind('blur', function() {
   if (!$.trim($(this).val()))
     $(this).val($('input[name="placeholdervalue"]', f).val())
       .addClass('placeholdervalue');
});
*/


$.getScript(JS_URLS.validate, function() {
   var validated_emails = {};
   
   $('form.login').validate({
      rules: {
         email: {
              required: true,
	      email: true
	 },
	 password: {
              required: true,
              minlength: 4
	 }
      },
      onkeyup: false,
      success: function(label_) {
         if (label_.attr('for') == 'email') {
            var value = $('input[name="email"]', 'form.login').val();
            if ($.inArray(value, validated_emails) == -1) {
               $.getJSON('/user/signup/', {validate_email:value}, function(response) {
                  if (!(response.error && response.error == 'taken')) {
                     $('label[for="email"]', 'form.login').text("No user by that email");
                  }
                  validated_emails[value] = response;
               });
            }
         }
      }
   });
   
   
   $('form#signup').validate({
      invalidHandler: function(form, validator) {
	 var errors = validator.numberOfInvalids();
	 if (errors)
           $('#invalid-anything:hidden').show(200);
      },
      rules: {
         email: {
              required: true,
	      email: true
	 },
	 password: {
              required: true,
              minlength: 4
	 }
      },
      onkeyup: false,
      success: function(label_) {
         if (!$('input.error', 'form#signup').size()) 
           $('#invalid-anything:visible').hide(400);
         var text = "OK!";
         if (label_.attr('for') == 'email') {
            var value = $('input[name="' + label_.attr('for') + '"]', 'form#signup').val();
            
            if ($.inArray(value, validated_emails) == -1) {
               $.getJSON('/user/signup/', {validate_email:value}, function(response) {
                  if (response.error) {
                     $('#invalid-email').show(200);
                     $('label[for="email"]', 'form#signup').text("Not ok").addClass('error').removeClass('valid');
                  } else {
                     $('#invalid-email:visible').hide();
                     $('label[for="email"]', 'form#signup').remove();
                     //$('label[for="email"]', 'form#signup').text("OK!").removeClass('error').addClass('valid');
                  }
                  validated_emails[value] = response;
               });
            }
         }
         label_.addClass("valid").text(text);
      }//,
      
      //errorLabelContainer: "form#signup .errormsgs",
      //wrapper: "li"
      
      
   });
});
//var email_pattern = new RegExp(/^(("[\w-\s]+")|([\w-]+(?:\.[\w-]+)*)|("[\w-\s]+")([\w-]+(?:\.[\w-]+)*))(@((?:[\w-]+\.)*\w[\w-]{0,66})\.([a-z]{2,6}(?:\.[a-z]{2})?)$)|(@\[?((25[0-5]\.|2[0-4][0-9]\.|1[0-9]{2}\.|[0-9]{1,2}\.))((25[0-5]|2[0-4][0-9]|1[0-9]{2}|[0-9]{1,2})\.){2}(25[0-5]|2[0-4][0-9]|1[0-9]{2}|[0-9]{1,2})\]?$)/i);
//var f2 = $('form.signup');
//$('input[name="email"]', f2).change(function() {
//  
//});
