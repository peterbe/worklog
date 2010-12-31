function L() {
   if (window.console && window.console.log)
   for (var i = 0, l = arguments.length; i < l; i++)
     console.log(arguments[i]);
}

function increment_total_no_events(new_no) {
  total_no_events += typeof new_no != 'undefined' ? new_no : 1;
  $('#total_no_events').text(total_no_events);
}

function decrement_total_no_events(new_no) {
  total_no_events -= typeof new_no != 'undefined' ? new_no : 1;
  $('#total_no_events').text(total_no_events);
}

$(function() {
   $('a.account').fancybox({
         'autoDimensions': false,
         'width'         : 550,
         'height'        : 400,
         'transitionIn': 'none',
         'transitionOut': 'none',
         onComplete: function(array, index, opts) {
            $.getScript(JS_URLS.account);
         }
   });
});      
