function display_sidebar_stats() {
   //var days_pie, hours_pie;
   var color_map = {};
   var seriesColors;
   var unused_colors;
   $.getJSON('/log/stats.json', {},
             function(response) {
      $('#actions-plot').html('');
                //alert(response.actions);
      if (response.actions) {
         $('#actions-plot:hidden').show();
           $.jqplot('actions-plot', [response.actions], {
              //seriesColors: response.days_colors,
             title: 'Actions',
             grid: { drawGridLines: false, gridLineColor: '#fff', background: '#fff',  borderColor: '#fff', borderWidth: 1, shadow: false },
             highlighter: {sizeAdjust: 7.5},
             seriesDefaults:{renderer:$.jqplot.PieRenderer, rendererOptions:{sliceMargin:3, padding:7, border:false}},
           legend:{show:true}
           });
      } else {
         $('#actions-plot:visible').hide();
      }
      
     $('#contexts-plot').html('');
      if (response.contexts) {
         $('#contexts-plot:hidden').show();
           $.jqplot('contexts-plot', [response.contexts], {
              //seriesColors: response.hours_colors,
             title: 'Contexts',
             grid: { drawGridLines: false, gridLineColor: '#fff', background: '#fff',  borderColor: '#fff', borderWidth: 1, shadow: false },
             seriesDefaults:{renderer:$.jqplot.PieRenderer, rendererOptions:{sliceMargin:3, padding:7, border:false}},
           legend:{show:true}
        });
      } else {
         $('#contexts-plot:visible').hide();
      }
      
   });
}

head.ready(function() {
   display_sidebar_stats();
});