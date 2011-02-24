
function display_sidebar_stats(start, end) {
   //var days_pie, hours_pie;
   var color_map = {};
   var seriesColors;
   var unused_colors;
   $.getJSON('/events/stats.json', {start: start.getTime(), end: end.getTime(), with_colors:true},
             function(response) {
      $('#days-plot').html('');
      if (response.days_spent && response.days_spent.length) {
         $('#days-plot:hidden').show();
         var days_plot =
           $.jqplot('days-plot', [response.days_spent], {
              seriesColors: response.days_colors,
             title: 'Days spent',
             grid: { drawGridLines: false, gridLineColor: '#fff', background: '#fff',  borderColor: '#fff', borderWidth: 1, shadow: false },
             highlighter: {sizeAdjust: 7.5},
             seriesDefaults:{renderer:$.jqplot.PieRenderer, rendererOptions:{sliceMargin:3, padding:7, border:false}},
	      legend:{show:true, border:'0px solid white'}
           });
      } else {
         $('#days-plot:visible').hide();
      }

     $('#hours-plot').html('');
      if (response.hours_spent && response.hours_spent.length) {
         $('#hours-plot:hidden').show();

         var hours_plot =
           $.jqplot('hours-plot', [response.hours_spent], {
              seriesColors: response.hours_colors,
             title: 'Hours spent',
             grid: { drawGridLines: false, gridLineColor: '#fff', background: '#fff',  borderColor: '#fff', borderWidth: 1, shadow: false },
             seriesDefaults:{renderer:$.jqplot.PieRenderer, rendererOptions:{sliceMargin:3, padding:7, border:false}},
           legend:{show:true, border:'0px solid white'}
        });
      } else {
         $('#hours-plot:visible').hide();
      }


      if (response.tag_colors) {
         $('span.fc-event-title').each(function() {
            $(this).html(_tag_highlight(response.tag_colors, $(this).text()));
         });
      }

   });
}

function _tag_highlight(colors, text) {
   var ncolors={};
   function f(m, n) {
      return '<span class="tag" style="background-color:' + ncolors[n.toLowerCase()] +'">' + m + '</span>';
   }
   // convert the associate dig to lower case
   for (var k in colors) {
      ncolors[k.toLowerCase()] = colors[k];
   }
   return text.replace(/\B[#@]([\w-]+)/ig, f);
}

//------------------------------------------------------------------------------
// By default, the CSS is loaded for the big display
var sidebar_hidden = false;
function _big_display() {
   //L("BIG");
   if (sidebar_hidden) {
      //L("    show sidebar");
      $('#sidebar:hidden').show();
      $('#wrap').css('width','95%');
      $('#content').css('width','70%');
      $('.footer-stats:hidden','#footer').show();
      $('#calendar').fullCalendar('render');
      sidebar_hidden = false;
   } else {
      //L("    do nothing");
   }
   L('in _big_display()');
   var view = $('#calendar').fullCalendar('getView');
   display_sidebar_stats(view.start, view.end);
}

function _small_dislay() {
   //L("SMALL");
   if (!sidebar_hidden) {
      $('#sidebar').hide();
      $('#wrap').css('width','100%');
      $('#content').css('width','100%');
      $('#calendar').fullCalendar('render');
      $('.footer-stats:visible','#footer').hide();
      big_display_loaded = false;
      sidebar_hidden = true;
   }
}

var jqplot_loaded = false;
head.ready(function() {
   head.js(JS_URLS.jqplot, JS_URLS.jqplot_pierenderer, function() {
      $.jqplot.config.enablePlugins = true;

      jqplot_loaded = true;
      var resize_timer;
      $(window).resize(function() {
	 //L($(window).width());
	 clearTimeout(resize_timer);
	 resize_timer = setTimeout(function() {
	    if ($(window).width() > 1200) {
	       _big_display();
	    } else {
	       _small_dislay();
	    }
	 }, 1000);
      });
      if ($(window).width() > 1100) {
	 var view = $('#calendar').fullCalendar('getView');
	 _big_display();
      } else {
	 _small_dislay();
      }
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
      'type': 'iframe',
      onClosed: function() {
	 if ($('#introduction-video:visible').size()) {
	    $('#introduction-video').hide();
	    $('#introduction-video-after').show('slow');
	 }
      }
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