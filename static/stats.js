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

function get_automatic_interval_string() {
   var d = daysDiff(startDate.datepicker('getDate'), endDate.datepicker('getDate'));
   if (d > 100) return '1 month';
   if (d > 30) return '1 week';
   return '1 day';
}

function get_automatic_date_format_string(interval) {
   if (interval == '1 month') return '%b %Y';
   if (interval == '1 week') return '%#d/%b -%y';
   return '%#d/%b';
}

function plot_users(cumulative, interval, date_format_string) {
   $('#plot-users').html('');
   var response_keys, series;
   if (cumulative) {
      response_keys = ['cum_w_email', 'cum_wo_email'];
      series = [
                {label:'Cumulative (with email)', lineWidth:4},
                {label:'Cumulative (no email)', lineWidth:4},
               ];
   } else {
      response_keys = ['new_w_email', 'new_wo_email'];
      series = [
                {label:'New (with email)', lineWidth:4},
                {label:'New (no email)', lineWidth:4}
               ];      
   }
   $.getJSON('/stats/users.json', {
      interval: interval,
      cumulative: cumulative,
      start: startDate.datepicker('getDate').getTime(),
	end: endDate.datepicker('getDate').getTime()}, 
             function(response) {
                var lines = new Array();
                $.each(response_keys, function(i, e) {
                   lines.push(response[e]);
                });
                $.jqplot('plot-users', lines,
                         {
                   title:'Users',
			      legend:{show:true, location:'nw'},
                     series:series,
                     
                     //gridPadding:{right:35},
              axes:{
                 yaxis:{
                    tickOptions:{
                       formatString: '%d'
                    },
                    min: 0
                 },
                 xaxis:{
                    renderer:$.jqplot.DateAxisRenderer,
                      tickOptions:{formatString:date_format_string},
                    min:startDate.datepicker('getDate'),
                      tickInterval:interval
                 }
              }
                });
             });

}
   
function plot_events(cumulative, interval, date_format_string) {
   $('#plot-events').html('');
   var response_keys, series;
   if (cumulative) {
      response_keys = ['cum'];
      series = [
                {label:'Cumulative', lineWidth:4},
               ];
   } else {
      response_keys = ['new'];
      series = [
                {label:'New', lineWidth:4}
               ];      
   }
   $.getJSON('/stats/events.json', {
      interval: interval,
      cumulative: cumulative,
      start: startDate.datepicker('getDate').getTime(),
	end: endDate.datepicker('getDate').getTime()},
             function(response) {
                var lines = new Array();
                $.each(response_keys, function(i, e) {
                   lines.push(response[e]);
                });
                $.jqplot('plot-events', lines,
                         {
                   title:'Events',
                     legend:{show:false},
                     series:series,
                     
                     
                     //gridPadding:{right:35},
              axes:{
                 yaxis:{
                    tickOptions:{
                       formatString: '%d'
                    },
                    min: 0
                 },
                 xaxis:{
                    renderer:$.jqplot.DateAxisRenderer, 
                      tickOptions:{formatString:date_format_string},
                    min:startDate.datepicker('getDate'),
                      tickInterval:interval
                 }
              }
                });
             });   
}

function update_numbers() {
   $('#numbers td').remove();
   $.getJSON('/stats/numbers.json', {
      start: startDate.datepicker('getDate').getTime(),
	end: endDate.datepicker('getDate').getTime()}, 
             function(response) {
                $.each(response.numbers, function(i, e) {
                   $('<tr></tr>').appendTo('#numbers')
                     .append($('<td></td>').text(e.label+':').addClass('label'))
                       .append($('<td></td>').text(e.number).addClass('number'));
                                                              
                });
             });
   
}


function plot_usersettings() {
   $('#plot-usersettings').html('');
   $.getJSON('/stats/usersettings.json', {
      start: startDate.datepicker('getDate').getTime(),
      end: endDate.datepicker('getDate').getTime()
   }, function(response) {
      $.jqplot('plot-usersettings', response.lines, {
        title:'Switched on settings',
        grid:{
            drawGridlines:true,
            background: '#ffffff',
            borderWidth: 0,
            shadow: false
        },
        stackSeries: true, 
        seriesColors: ["#82BC24","#ffffff"],
        seriesDefaults: {
            renderer: $.jqplot.BarRenderer,
            rendererOptions:{barMargin: 25}, 
            pointLabels:{stackedValue: true},
            yaxis:'y2axis',
            shadow: false
        },
        series:[
            {pointLabels:{ypadding: -15}},
            {pointLabels:{ypadding:9000}}   // this hack will push the labels for the top series off of the page so they don't appear.
        ],
        axes: {
            xaxis:{
                ticks: response.labels,
                renderer:$.jqplot.CategoryAxisRenderer, 
                tickOptions:{
                    showGridline:false, 
                    markSize:0
                }
            },
            y2axis:{
                ticks:[0, 100], 
                tickOptions:{formatString:'%d\%'}
            }
        }
    });

   });
}

function refresh_date_range() {
   update_numbers();
   var interval = get_automatic_interval_string();
   var date_format_string = get_automatic_date_format_string(interval);
   var cumulative = $('#cumulative:checked').size();
   plot_users(cumulative, interval, date_format_string);
   plot_events(cumulative, interval, date_format_string);
   plot_usersettings();
}

$(function() {
   $.jqplot.config.enablePlugins = true;
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
   
   $('input#cumulative, input#not_cumulative').change(function() {
      refresh_date_range();
   });

   resync();
   refresh_date_range();   
});