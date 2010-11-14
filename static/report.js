function L() {
   console.log.apply(console, arguments);
}

// Note: variables minDate and maxDate are prepared in the template
// 
var slider;
var startDate;
var endDate;
var dateformat = 'd M yy';



function resync(values) {
   if (values) {
      var date = new Date(minDate.getTime());
      date.setDate(date.getDate() + values[0]);
      startDate.val($.datepicker.formatDate(dateformat, date));
      date = new Date(minDate.getTime());
      date.setDate(date.getDate() + values[1]);
      endDate.val($.datepicker.formatDate(dateformat, date));
   } else {
      var start = daysDiff(minDate, startDate.datepicker('getDate') || minDate);
      var end = daysDiff(minDate, endDate.datepicker('getDate') || maxDate);
      start = Math.min(start, end);
      slider.slider('values', 0, start);
      slider.slider('values', 1, end);
   }
   startDate.datepicker('option', 'maxDate', endDate.datepicker('getDate') || maxDate);
   endDate.datepicker('option', 'minDate', startDate.datepicker('getDate') || minDate);
   
   
   $('a.download-export').each(function(i, e) {
      var href = $(this).attr('href');
      if (href.search(/start=/)==-1) {
         href += '?start=' + startDate.datepicker('getDate').getTime() + 
	   '&end=' + endDate.datepicker('getDate').getTime();
      } else {
         href = href.replace(/start=(\d+)/, 'start=' + startDate.datepicker('getDate').getTime());
         href = href.replace(/end=(\d+)/, 'end=' + endDate.datepicker('getDate').getTime());
      }
      $(this).attr('href', href);
   });
}

function daysDiff(d1, d2) {
    return  Math.floor((d2.getTime() - d1.getTime()) / 86400000);
}

function refresh_date_range() {
   $('#report').fadeTo(0, 0.2);
   //console.log(startDate.datepicker('getDate').getTime());
   //console.log(endDate.datepicker('getDate').getTime());
   $.getJSON('/report.json', {
    start: startDate.datepicker('getDate').getTime(),
    end: endDate.datepicker('getDate').getTime()}, function(response) {
       $('tbody#days_spent tr').remove();
       if (response.days_spent && response.days_spent.length) {
          var total = 0.0;
          $.each(response.days_spent, function(i, e) {
             $('tbody#days_spent').append(
               $('<tr></tr>').append(
                 $('<td></td>').html(e[0]).addClass('label')
                ).append($('<td></td>').text(e[1])));
             total += e[1];                                      
          });
          $('tbody#days_spent').append(
             $('<tr></tr>').addClass('total').append(
               $('<td></td>').text('Total').addClass('label')
                ).append($('<td></td>').text(total)));
	  
	  $.jqplot('days-plot', [response.days_spent], {
             title: '',
             grid: { drawGridLines: false, gridLineColor: '#fff', background: '#fff',  borderColor: '#fff', borderWidth: 1, shadow: false },
             highlighter: {sizeAdjust: 7.5},
             seriesDefaults:{renderer:$.jqplot.PieRenderer, rendererOptions:{sliceMargin:3, padding:7, border:false}},
             legend:{show:true}
	  });
	  
       }
       
       $('tbody#hours_spent tr').remove();
       if (response.hours_spent && response.hours_spent.length) {
          var total = 0.0;
          $.each(response.hours_spent, function(i, e) {
             $('tbody#hours_spent').append(
               $('<tr></tr>').append(
                 $('<td></td>').html(e[0]).addClass('label')
                ).append($('<td></td>').text(e[1])));
             total += e[1];                                      
          });
          $('tbody#hours_spent').append(
             $('<tr></tr>').addClass('total').append(
               $('<td></td>').text('Total').addClass('label')
                ).append($('<td></td>').text(total)));
          
          $.jqplot('hours-plot', [response.hours_spent], {
             title: '',
             grid: { drawGridLines: false, gridLineColor: '#fff', background: '#fff',  borderColor: '#fff', borderWidth: 1, shadow: false },
             seriesDefaults:{renderer:$.jqplot.PieRenderer, rendererOptions:{sliceMargin:3, padding:7, border:false}},
           legend:{show:true}
          });          
       }
       
       
       
       $('#report').fadeTo(200, 1.0);

    });
    
}


$(function() {
   $.jqplot.config.enablePlugins = true;
   
   var hash_code_regex = /(\d{4}),(\d{1,2}),(\d{1,2})/;
   if (hash_code_regex.test(location.hash)) {
      var _match = location.hash.match(hash_code_regex);
      var year = parseInt(_match[1]);
      var month = parseInt(_match[2]) - 1;
      var day = parseInt(_match[3]);
      var d = new Date(year, month, day);
      $('#from_date').val($.datepicker.formatDate(dateformat, d));
      if (month == 11) {
        var d2 = new Date(year+1, 0, 1);
      } else {
         var d2 = new Date(year, month+1, 1);
      }
      d2 = new Date(d2.getTime() - 1000 * 3600 * 24);
      if (d2 > maxDate) 
        d2 = maxDate;
      $('#to_date').val($.datepicker.formatDate(dateformat, d2));
   }
   
   if (!$('#from_date').val()) {
      $('#from_date').val($.datepicker.formatDate(dateformat, minDate));
   }
   if (!$('#to_date').val()) {
      $('#to_date').val($.datepicker.formatDate(dateformat, maxDate));
   }
    
    slider = $('#slider').slider({range: true, max: daysDiff(minDate, maxDate),
            stop: function(event, ui) {
              still_sliding = false;
              refresh_date_range();
            },
            slide: function(event, ui) { resync(ui.values); }});
    startDate = $('#from_date').datepicker({
        firstDay: SETTINGS.monday_first ? 1 : 0,
        minDate: minDate, 
        maxDate: maxDate,
        dateFormat: dateformat,
        onSelect: function(dateStr) { 
          resync();
          refresh_date_range();
        }}).
        keyup(function() { resync(); });
    endDate = $('#to_date').datepicker({
        firstDay: SETTINGS.monday_first ? 1 : 0,
            minDate: minDate, 
            maxDate: maxDate,
            dateFormat: dateformat,
            onSelect: function(dateStr) { 
              resync();
              refresh_date_range();
            }}).
        keyup(function() { resync(); });
   

   resync();
   refresh_date_range();
});
