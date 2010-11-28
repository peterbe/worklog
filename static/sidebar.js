
function display_sidebar_stats(start, end) {
   //var days_pie, hours_pie;
   var color_map = {};
   var seriesColors;
   var unused_colors;
   $.getJSON('/events/stats.json', {start: start.getTime(), end: end.getTime(), with_colors:true},
             function(response) {
      if (response.days_spent && response.days_spent.length) {
         //$('#days-plot:hidden').show();
         $('#days-plot').html('');
         var days_plot = 
           $.jqplot('days-plot', [response.days_spent], {
              seriesColors: response.days_colors,
             title: 'Days spent',
             grid: { drawGridLines: false, gridLineColor: '#fff', background: '#fff',  borderColor: '#fff', borderWidth: 1, shadow: false },
             highlighter: {sizeAdjust: 7.5},
             seriesDefaults:{renderer:$.jqplot.PieRenderer, rendererOptions:{sliceMargin:3, padding:7, border:false}},
           legend:{show:true}
           });
         //L("LEFT", seriesColors.slice(highest_i+1, seriesColors.length));
      } else {
         //$('#days-plot:visible').hide();
      }
      
      if (response.hours_spent && response.hours_spent.length) {
         $('#hours-plot:hidden').show();
         var hours_plot = 
           $.jqplot('hours-plot', [response.hours_spent], {
              seriesColors: response.hours_colors,
             title: 'Hours spent',
             grid: { drawGridLines: false, gridLineColor: '#fff', background: '#fff',  borderColor: '#fff', borderWidth: 1, shadow: false },
             seriesDefaults:{renderer:$.jqplot.PieRenderer, rendererOptions:{sliceMargin:3, padding:7, border:false}},
           legend:{show:true}
        });
      } else {
         $('#hours-plot:visible').hide();
      }
      
   });
}


var jqplot_loaded = false;
$(function() {
   $.getScript(JS_URLS.jqplot, function() {
      $.getScript(JS_URLS.jqplot_pierenderer, function() {
         var view = $('#calendar').fullCalendar('getView');
         jqplot_loaded = true;
         display_sidebar_stats(view.start, view.end);
      });
   });

   $('a.user-settings').fancybox({
      'width': '75%',
      'height': '75%',
      'scrolling': 'no',
      'transitionIn': 'none',
      'transitionOut': 'none',
      //'type': 'iframe',
      onComplete: function() {
	 //location.href='/'; // works but not ideal
         if (location.hash) {
            $('<input name="anchor" type="hidden">').val(location.hash).appendTo($('form.user-settings'));
         }
      }
   });
   
   $('a.vimeovideo').fancybox({
      'width': '60%',
      'height': '65%',
      'transitionIn': 'none',
      'transitionOut': 'none',
      'type': 'iframe'
   });
      
   $('a.share').fancybox({
      'width': '75%',
      'height': '75%',
      'scrolling': 'no',
      'transitionIn': 'none',
      'transitionOut': 'none',
      onComplete: function(array, index, opts) {
         $.getScript(JS_URLS.jquery_form, function() {
            $.getScript(JS_URLS.jquery_ui_droppable, function() {
               $.getScript(JS_URLS.share);
            });
         });
      }
   });
});