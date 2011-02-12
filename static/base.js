function L() {
   console.log.apply(console, arguments);
}

function increment_total_no_events(new_no) {
  total_no_events += typeof new_no != 'undefined' ? new_no : 1;
  $('#total_no_events').text(total_no_events);
}

function decrement_total_no_events(new_no) {
  total_no_events -= typeof new_no != 'undefined' ? new_no : 1;
  $('#total_no_events').text(total_no_events);
}

/*

*/

$.getJSON('/auth/logged_in.json', function(r) {
   if (r.redirect_to) {
      window.location.href = r.redirect_to;
      return;
   }
   if (r.user_name) {
      $('#login').removeClass('login_not');
      if (r.premium) {
         $('#login').addClass('login_premium');
         $('a.account','#login').attr('title','You\'re a premium user!');
      } else {
         $('#login').addClass('login_user');
      }
      $('a.account','#login').text('Hi ' + r.user_name);
      $('#login p').append($('<a>', {text:'log out',
               href:'/auth/logout/'}).addClass('log-out'));
      $('#report-link').show();
   } else {
      $('#introduction').show();
   }
});