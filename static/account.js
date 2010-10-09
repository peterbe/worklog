/* this is loaded automatically when the account page is shown */

var f = $('form.login');
var e = $('input[name="email"]', f);
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


//$.getJSON('/user/account.json', function(response) {
//   if (response.email)
//     $('input[name="email"]').val(response.email);
//});

