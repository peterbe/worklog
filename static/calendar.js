function L() {
   if (window.console && window.console.log)
   for (var i = 0, l = arguments.length; i < l; i++)
     console.log(arguments[i]);
}



function __standard_qtip_options() {
  return {
     position: {
        corner: {
        target: 'bottomMiddle',
        tooltip: 'topMiddle'
     }, 
     adjust: {
        screen: true
     }
   },
   show: {
      when: 'click',
      ready: true,
      solo:true
   },
   hide: 'unfocus',
   style: {
        tip: true, // Apply a speech bubble tip to the tooltip at the designated tooltip corner
        border: {
           width: 0,
           radius: 3,
             color: '#3366CC'
        },
         title: {
            background:'#3366CC',
              color: '#fff'
         },
        background: '#7094db',
        color: '#fff',
        name: 'dark', // Use the default light style
        width: 470 // Set the tooltip width
      }
  };
}

/* Return a jQuery type DOM form element */
function get_add_form(action, date, all_day) {
   var f = $('#add-form');
   f.attr('action', action);
   $('input[name="date"]', f).val(date.getTime());
   if (all_day)
     $('input[name="all_day"]', f).val('1');
   else
     $('input[name="all_day"]', f).val('');
   return f;
   
   /*
   var f = $('<form method="post"></form>').attr('action', action);
   var d = $('<div></div>');
   var t = $('<input name="title" id="id_title" size="35">');
   d.append(t);
   d.append($('<input type="submit" value="Save">'));
   if (all_day)
     d.append($('<input type="hidden" name="all_day" value="1">'));
   d.append($('<input type="hidden" name="date">').val(date.getTime()));
   f.append(d);
   return f;
    */
}
/*
function get_edit_form(action, id, title, url) {
   var f = $('#edit-form');
   f.attr('action', action);
   
   // reset anything if the edit form has been used before
   $('.edit-url:visible', f).hide();
   $('.see-url:visible', f).hide();
   $('a.delete:hidden', f).show();
   $('.confirmation', f).hide();
   
   $('input[name="title"]', f).val(title);
   $('input[name="id"]', f).val(id);
   if (url) {
      $('input[name="url"]', f).val(url);
      $('.see-url', f).html('').append(
        $('<a href="#"></a>').text(url).click(function() {
           window.open=url;
        })
      ).show();
   } else {
      $('.edit-url', f).show();
   }
   $('a.delete', f).click(function() {
      var parent = $(this).parents('div.delete');
      $('.confirmation', parent).show();
      $(this).hide();
      $('.delete-confirm', parent).click(function() {
         return false;
      });
      $('.delete-cancel', parent).click(function() {
         $('div.delete .confirmation:visible').hide(400);
         $(this).show(500);
         return false;
      });
      return false;
   });
   
   return f;
   
   var f = $('<form method="post"></form>').attr('action', action);
   var d = $('<div></div>');
   d.append($('<input name="title" id="id_title" size="35">').val(title));
   d.append($('<input type="submit" value="Save">'));
   d.append($('<input type="hidden" name="id">').val(id));
   f.append(d);
   return f;
}
*/

/*
function OOOOLLLLDDD____event_clicked(calEvent, jsEvent, view) {
        //alert('Event: ' + calEvent.title);
        //alert('Coordinates: ' + jsEvent.pageX + ',' + jsEvent.pageY);
        //alert('View: ' + view.name);

        // change the border color just for fun
        $(this).qtip({
           content: {
              text: calEvent.title//,
              //title: {
              //   text: calEvent.title,
              //   button: 'Close'
              //}
           }, 
      position: {
         corner: {
            target: 'bottomMiddle',
            tooltip: 'topMiddle'
         },
         adjust: {
            screen: true
         }
      },
      show: {
         when: 'click',
         ready: true,
         solo:true
      },
      hide: 'unfocus',
      style: {
        tip: true, // Apply a speech bubble tip to the tooltip at the designated tooltip corner
        border: {
           width: 0,
           radius: 3,
	     color: '#3366CC'
        },
	 title: {
            background:'#3366CC',
	      color: '#fff'
	 },
        background: '#7094db',
        color: '#fff',
        name: 'dark'//, // Use the default light style
        //width: 470 // Set the tooltip width
      }
   });
  
}
*/

var current_tooltip;
function _day_clicked(date, allDay, jsEvent, view) {
   var url = "/events";
   var qtip_options = {
      content: {
           //text: "Please wait...",
	   text: get_add_form(url, date, allDay)
	   //url: url//,
	   //title: {
           //  text: "Adding new event",
	   //  button: "Cancel"
	   //}
      },
      api: {
        onShow: function(event) {
           $('form:visible').submit(function() {
              _setup_ajaxsubmit(this);
              return false;
           });
        }
      }
   };
   qtip_options = $.extend(qtip_options, __standard_qtip_options());
   current_tooltip = $(this);
   current_tooltip.qtip(qtip_options);
   setTimeout(function() {
      $('input[name="title"]:visible').focus();
      __setup_tag_autocomplete($('input[name="title"]:visible'));
   }, 500);
}

function _event_clicked(event, jsEvent, view) {
   var url = "/event/edit?id=" + event.id;
   var qtip_options = {
      content: {
           text: "Please wait...",
	   //text: get_edit_form(url, event.id, event.title, event.url)
	   url: url,
	   //title: {
           //  text: "Adding new event",
	   //  button: "Cancel"
	   //}
      },
      api: {
          onContentUpdate: function() {
	     $('form.edit').submit(function() {
		_setup_ajaxsubmit(this, event.id);
		return false;
	     });
             $('input[name="title"]').focus();
             if (!$('input[name="url"]').val()) {
                $('input[name="url"]')
                  .addClass('placeholdervalue')
                  .val($('input[name="placeholdervalue"]').val());
             }
             
             $('input[name="url"]').bind('focus', function() {
                if ($(this).val() == $('input[name="placeholdervalue"]').val()) {
                   $(this).val('').removeClass('placeholdervalue');
                }
             }).bind('blur', function() {
                if (!$.trim($(this).val()))
                  $('input[name="url"]')
                    .addClass('placeholdervalue')
                      .val($('input[name="placeholdervalue"]').val());
             });
          }
      }
   };
   qtip_options = $.extend(qtip_options, __standard_qtip_options());
   current_tooltip = $(this);
   current_tooltip.qtip(qtip_options);
}

function _event_resized(event,dayDelta,minuteDelta,revertFunc, jsEvent, ui, view) {
   //revertFunc();
   $.post("/event/resize", {days:dayDelta, minutes:minuteDelta, id:event.id}, function(response) {
      if (response.error) {
         alert(response.error);
         revertFunc();
      }
      display_sidebar_stats_wrapped(view.start, view.end);
   });
}

function _event_dropped(event,dayDelta,minuteDelta,allDay,revertFunc) {
   $.post("/event/move", {days:dayDelta, minutes:minuteDelta, id:event.id}, function(response) {
      if (response.error) {
         alert(response.error);
         revertFunc();
      }
   });   
}

function __setup_tag_autocomplete(jelement) {
   function split( val ) {
      return val.split( /\s+/ );
   }
   function extractLast( term ) {
      return split( term ).pop();
   }

   jelement.autocomplete({
      minLength: 1,
      delay: 100,
      source: function( request, response ) {
         // delegate back to autocomplete, but extract the last term
         
         if (extractLast(request.term).charAt(0) != '@')
           response( []);
         else {
            response( $.ui.autocomplete.filter(
                                               AVAILABLE_TAGS, extractLast( request.term ) ) );
         }
      },
      focus: function() {
         // prevent value inserted on focus
         return false;
      },
      select: function( event, ui ) {
         var terms = split( this.value );
         // remove the current input
         terms.pop();
         // add the selected item
         terms.push( ui.item.value );
         // add placeholder to get the comma-and-space at the end
         terms.push( "" );
         this.value = terms.join( " " );
         return false;
      }
   });
}

function _setup_ajaxsubmit(element, event_id) {
   
      $(element).ajaxSubmit({
         beforeSubmit: function(arr, form, options) {
	    var _all_good = true;
	    $.each(arr, function(i, e) {
	       if (e.name=='task')
		 if (!$.trim(e.value)) {
		    _all_good = false;
		 }
	    });
	    return _all_good;
	 },
         success: function(response) {
	    if (response.error)
	      alert(response.error);

	    // close any open qtip
	    if (current_tooltip) {
               current_tooltip.qtip("hide");
            }
            
 	    //if (response.event) {
            //   $('#calendar').fullCalendar('removeEvents', event_id);
            //   $('#calendar').fullCalendar('renderEvent', response.event, false);
            //}
            if (response.tags)
              $.each(response.tags, function(i, tag) {
                if ($.inArray(tag, AVAILABLE_TAGS)==-1)
                   AVAILABLE_TAGS.push(tag);
              });
	    
            if (!response.error) {
               $('#calendar').fullCalendar('refetchEvents');
               $('#calendar').fullCalendar('render');
            }
	 }
      });   
}

/* In a "share" we can expect there to be a name,
 * a className and a key so that that particular share can be hidden
 */
var colors = '#5C8D87,#994499,#6633CC,#B08B59,#DD4477,#22AA99,#668CB3,#DD5511,#D6AE00,#668CD9,#3640AD'.split(',');
var described_classNames = new Array();
function __display_current_sharers(sharers) {
   var container = $('#current-sharers ul');
   var any = false;
   $.each(sharers, function(i, share) {
      L(share.className);
      var className = share.className;
      described_classNames.push(className);
      var color = colors[$.inArray(className, described_classNames)];
      
      container.append($('<li></li>')
                       .css('background-color', color)
                       .append($('<a href="#"></a>')
                               .text(share.full_name)));
      $('.' + className + ', .fc-agenda .' + className + ' .fc-event-time, .' + className + ' a'
          ).css('background-color', color).css('border-color', color);
      
      any = true;
   })
   if (any)
     $('#current-sharers').show();
}

var AVAILABLE_TAGS = [];

$(function() {
   var defaultView = 'month';
   if (location.hash.search('#week') == 0)
     defaultView = 'agendaWeek';
   else if (location.hash.search('#day') == 0)
     defaultView = 'agendaDay';
   var today = new Date();
   var year = today.getFullYear();
   var month = today.getMonth();
   var day = undefined;
   var hash_code_regex = /(\d{4}),(\d{1,2}),(\d{1,2})/;
   if (hash_code_regex.test(location.hash)) {
      var _match = location.hash.match(hash_code_regex);
      year = parseInt(_match[1]);
      month = parseInt(_match[2]) - 1;
      day = parseInt(_match[3]);
   }
   
   $('#calendar').fullCalendar({
      //events: '/events.json',
      events: function(start, end, callback) {
 	var url = '/events.json?start=' + start.getTime() + '&end=' + end.getTime();
 	$.getJSON(url, function(response) {
           callback(response.events);
           if (response.sharers)
             __display_current_sharers(response.sharers);
           if (response.tags)
             $.each(response.tags, function(i, tag) {
                if ($.inArray(tag, AVAILABLE_TAGS)==-1)
                  AVAILABLE_TAGS.push(tag);
             });
        });
      },
       
      header: {
           left: 'prev,next today',
           center: 'title',
           right: 'month,agendaWeek,agendaDay'
      },
      year: year,
      month: month,
      date: day,
      defaultView: defaultView,
      editable: true,
      firstDay: SETTINGS.monday_first ? 1:0,
      weekends: !SETTINGS.hide_weekend,
      eventClick: _event_clicked,
      dayClick: _day_clicked,
      eventResize: _event_resized,
      eventDrop: _event_dropped,
      viewDisplay: function(view) {
	 display_sidebar_stats_wrapped(view.start, view.end);
         
         var href = '#' +view.name.replace('agenda','').toLowerCase();
         href += "," + view.start.getFullYear();
         href += "," + (view.start.getMonth() + 1);
         href += "," + view.start.getDate();
         location.href = href;
      }
  });
   
//   $('form').live('submit', function() {
//      return false;
//   });
   
   
   
   //$.getJSON('/events/tags.json', function(response) {
   //   AVAILABLE_TAGS = response.tags;
   //});
   
   
});

// Because this file is loaded before stats.js
// We can't yet use display_sidebar_stats() since that function might not yet
// have been created. So until then we will use a function to avoid a
// 'display_sidebar_stats is not defined' error
display_sidebar_stats_wrapped = function(start, end) {
   if (typeof display_sidebar_stats != 'undefined')
     display_sidebar_stats(start, end);
   
};