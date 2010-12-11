$(function() {
   var format_ampm = function(h, m) {
      var s='am';
      if (h > 12) {
         h = (h - 12);
         s = 'pm';
      }
      if (m) {
         return h + '.' + m + s;
      } else {
         return h + s;
      }
   };
   
   $('form select').change(function() {
      var h = parseInt($('select[name="time_hour"]').val());
      var m = parseInt($('select[name="time_minute"]').val());
      $('#as_ampm').text('(' + format_ampm(h, m) + ')');
   });
   $('form select').trigger('change');
   
   if ($('#id_tz_offset').size() && !$('#id_tz_offset').val()) {
      var d = new Date();
      var gmtHours = -d.getTimezoneOffset()/60;
      $('#id_tz_offset').val(gmtHours);
   }
   
   $('form#reminders').submit(function() {
      if (!$('input[name="weekdays"]:checked').size()) {
         alert("Please select at least one weekday");
         return false;
      }
      return true;
   });
   
   $('input[name="cancel"]').click(function() {
      window.location = '/emailreminders/';
   });
});
