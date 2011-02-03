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