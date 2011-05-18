head.ready(function(){

   $.getJSON('/log/activity.json', {}, function(response) {
      var plot = $.jqplot('users-plot', [response.users], {
         title:'Active Users',
           gridPadding:{right:35},
         axes:{
            yaxis: { min:0 },
            xaxis:{
               renderer:$.jqplot.DateAxisRenderer,
                 tickOptions:{formatString:'%#d %b -%y'}
               //min:'May 30, 2008',
               //  tickInterval:'1 month'
            }
         },
         series:[{lineWidth:2}]
      });

      var plot = $.jqplot('events-plot', [response.events], {
         title:'Active Events',
           gridPadding:{right:35},
         axes:{
            yaxis: { min:0 },
            xaxis:{
               renderer:$.jqplot.DateAxisRenderer,
                 tickOptions:{formatString:'%#d %b -%y'}
               //min:'May 30, 2008',
               //  tickInterval:'1 month'
            }
         },
         series:[{lineWidth:2}]
      });

   });
});
