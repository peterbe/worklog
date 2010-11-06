function L() {
   if (window.console && window.console.log)
   for (var i = 0, l = arguments.length; i < l; i++)
     console.log(arguments[i]);
}


function __standard_qtip_options() {
  return {
   show: {
      when: 'click',
      ready: true,
      solo: true
   },
   hide: 'unfocus',
       
  };
}

/* Return a jQuery type DOM form element */
/*
function get_add_form(action, date, all_day) {
   var f = $('#add-form');
   f.attr('action', action);
   $('input[name="date"]', f).val(date.getTime());
   if (all_day)
     $('input[name="all_day"]', f).val('1');
   else
     $('input[name="all_day"]', f).val('');
   return f;
}*/

var current_tooltip;
function _day_clicked(date, allDay, jsEvent, view) {
   var url = '/events';
   // need to set date and allDay into $('#add-form-container form')
   $('#add-form-container form').attr('action', url);
   if (allDay)
     $('#add-form-container input[name="all_day"]').val('1');
   else
     $('#add-form-container input[name="all_day"]').val('');
   $('#add-form-container input[name="date"]').val(date.getTime());
   
   var qtip_options = {
      content: {
	   text: $('#add-form-container').html()
      },
     position: {
          my: 'bottom middle',
	  at: 'center',
 	 // important so it doesn't move when move the mouse
          //target: 'event'
          target:this
      },
      hide: {
         event: false
      },
      show: {
           solo: true,
           ready:true,
           event: 'click'  
      },
      style: {
          classes: 'ui-tooltip-shadow',
          tip: {
              corner: 'middle bottom' 
          }
      },
      events: {
        render: function(event, api) {
           $('form:visible').submit(function() {
	      //if (!SETTINGS.disable_sound && soundManager.enabled) {
              //    soundManager.play('pling');
              // }
              _setup_ajaxsubmit(this);
              return false;
           });
	   __setup_tag_autocomplete($('input[name="title"]:visible'));
	   $('input[name="title"]:visible').focus();
        },
	hide: function(event, api) {
	    //L("hide!");
	     //api.destroy();
	}
	 
      }
   };
   //qtip_options = $.extend(qtip_options, __standard_qtip_options());
   current_tooltip = $(this);
   //current_tooltip.css('border', '2px solid red');
   //L(current_tooltip, current_tooltip.qtip());
   
   current_tooltip.qtip(qtip_options);
   //var api = current_tooltip.qtip();
}

function _event_clicked(event, jsEvent, view) {
   // by default events don't have the 'editable' attribute. It's usually only
   // set when the event is explcitely *not* editable.
   var is_editable = true;
   if (typeof event.editable != 'undefined')
     is_editable = event.editable;
   
   if (is_editable)
     var url = '/event.json?id=' + event.id;
   else
     var url = '/event.html?id=' + event.id;
   
   function _prepare_edit_event() {
      $('form.edit').submit(function() {
         _setup_ajaxsubmit(this, event.id);
         return false;
      });
      if ($('form.edit input[name="title"]:visible').size()) {
	 __setup_tag_autocomplete($('form.edit input[name="title"]'));
	 $('form.edit input[name="title"]').focus();
      } else {
	 // it hasn't been loaded yet :(
	 setTimeout(function() {
	    __setup_tag_autocomplete($('form.edit input[name="title"]'));
	    $('form.edit input[name="title"]').focus();
	 }, 500);
      }
      
      if (!$('input[name="external_url"]').val()) {
         $('input[name="external_url"]')
           .addClass('placeholdervalue')
             .val($('input[name="placeholdervalue"]').val());
      }
      
      $('input[name="external_url"]').bind('focus', function() {
         if ($(this).val() == $('input[name="placeholdervalue"]').val()) {
            $(this).val('').removeClass('placeholdervalue');
         }
      }).bind('blur', function() {
         if (!$.trim($(this).val()))
           $('input[name="external_url"]')
             .addClass('placeholdervalue')
               .val($('input[name="placeholdervalue"]').val());
         else if ($(this).val().search('://') == -1)
           $(this).val('http://' + $(this).val());
      });
      
      L($('a.delete'));
      $('a.delete').click(function() {
         var container = $(this).parents('div.delete');
         $('.confirmation', container).show();
         $('a.delete', container).hide();
         
         //$('a.delete-cancel', container).unbind('click');
         $('a.delete-confirm', container).click(function() {
            close_current_tooltip();
            $.post('/event/delete', {id: event.id}, function() {
               decrement_total_no_events();
               $('#calendar').fullCalendar('removeEvents', event.id);
	       //__update_described_colors();
	       var view = $('#calendar').fullCalendar('getView');
	       display_sidebar_stats_wrapped(view.start, view.end);
	       __update_described_colors();
               //$('#calendar').fullCalendar('refetchEvents');
               //$('#calendar').fullCalendar('render');
               
            });
            return false;
         });
         
         $('a.delete-cancel', container).unbind('click');
         $('a.delete-cancel', container).click(function() {
            var container = $(this).parents('div.delete');
            $('a.delete').show();
            $('.confirmation').hide();
         });
         return false
      });
   }
   
   /* This function is called when the qtip has opened for previewing */
   function _prepare_preview_event() {
      
   }
   
   var qtip_options = {
      content: {
          ajax: {
            url:url,
               success: function(data, status) {
                  L($('#edit-form-container input[name="title"]').val());
                  var clone = $('#edit-form-container').clone();
                  $('input[name="title"]', clone).val(data.title);
                  $('input[name="id"]', clone).val(data.id);
                  this.set('content.text', clone);
                  return false;
                  //if (is_editable)
                  //  _prepare_edit_event();
                  //else
                  //  _prepare_preview_event();                  
               }
          }
      },
     position: {
          my: 'bottom middle',
	  at: 'center',
 	 // important so it doesn't move when move the mouse
          //target: 'event'
          target:this
      },
      hide: {
         event: false
      },
      show: {
           solo: true,
           ready:true,
           event: 'click'  
      },
      style: {
          classes: 'ui-tooltip-shadow',
          tip: {
              corner: 'middle bottom' 
          }
      },
      events: {
        show: function(event, api) {
           L("show!");
        },
        render: function(event, api) {
           L("render");
           
      //       if (is_editable)
      //         _prepare_edit_event();
      //       else
      //         _prepare_preview_event();
        }
      }
   };
 
   /*
   var qtip_options = {
      content: {
           text: 'Please wait...',
	   //text: get_edit_form(url, event.id, event.title, event.url)
	   url: url
	   //title: {
           //  text: "Adding new event",
	   //  button: "Cancel"
	   //}
      },
      api: {
          onContentUpdate: function() {
             // for some reason qtip fires onContentUpdate() twice. The only difference
             // between the two times is this.cache.toggle
             if (!this.cache.toggle) return;
             if (is_editable)
               _prepare_edit_event();
             else
               _prepare_preview_event();
          }
      }
   };
    */
   //qtip_options = $.extend(qtip_options, __standard_qtip_options());
   current_tooltip = $(this);
   current_tooltip.qtip(qtip_options);
}

function _event_resized(event,dayDelta,minuteDelta,revertFunc, jsEvent, ui, view) {
   __update_described_colors();
   $.post('/event/resize', {days: dayDelta, minutes: minuteDelta, id: event.id}, function(response) {
      if (response.error) {
         alert(response.error);
         revertFunc();
      }
      display_sidebar_stats_wrapped(view.start, view.end);

   });
}

function _event_dropped(event,dayDelta,minuteDelta,allDay,revertFunc) {
   __update_described_colors();
   $.post('/event/move', {all_day:allDay, days: dayDelta, minutes: minuteDelta, id: event.id}, function(response) {
      if (response.error) {
         alert(response.error);
         revertFunc();
      }
   });
}

function __setup_tag_autocomplete(jelement) {
   function split(val ) {
      return val.split(/\s+/);
   }
   function extractLast(term ) {
      return split(term).pop();
   }
   
   jelement.autocomplete(AVAILABLE_TAGS, {
	autoFill: false,
	multiple: true,
	multipleSeparator: ' ',
	formatItem: function(row) {
	   return row[0] + ' ';
	}
   });
   /*
   jelement.autocomplete(
      minLength: 1,
      delay: 100,
      source: function(request, response ) {
         // delegate back to autocomplete, but extract the last term

         if (extractLast(request.term).charAt(0) != '@')
           response([]);
         else {
            response($.ui.autocomplete.filter(
                                               AVAILABLE_TAGS, extractLast(request.term)));
         }
      },
      focus: function() {
         // prevent value inserted on focus
         return false;
      },
      select: function(event, ui ) {
         var terms = split(this.value);
         // remove the current input
         terms.pop();
         // add the selected item
         terms.push(ui.item.value);
         // add placeholder to get the comma-and-space at the end
         terms.push('');
         this.value = terms.join(' ');
         return false;
      }
   });
    */
}

function _setup_ajaxsubmit(element, event_id) {
   $.getScript(JS_URLS.jquery_form, function() {
      if (is_offline) {
	 __inner_setup_ajaxsubmit_offline(element, event_id);	
      } else {
	 __inner_setup_ajaxsubmit(element, event_id);
      }
   });
}

function __inner_setup_ajaxsubmit_offline(element, event_id) {
   
   $(element).ajaxSubmit({beforeSubmit: function(arr, form, options) {
      if (!__beforeSubmit_form_validate(arr, form, options)) {
	 // consider showing a validation error
	 return;
      }
	 
      // assume that all will go well
      //       
      if (!event_id)
	increment_total_no_events();
      
      // close any open qtip
      close_current_tooltip();
      
      //if (event_id)
      // $('#calendar').fullCalendar('removeEvents', event_id);
      // 
	       
      //$('#calendar').fullCalendar('renderEvent', response.event);
      //var view = $('#calendar').fullCalendar('getView');
      //display_sidebar_stats_wrapped(view.start, view.end);
      //__update_described_colors();
   
   }
   });
   
}

function __beforeSubmit_form_validate(arr, form, options) {
   var _all_good = true;
   $.each(arr, function(i, e) {
      if (e.name == 'title')
	if (!$.trim(e.value)) {
	   _all_good = false;
	}
   });
   return _all_good;
}

function __inner_setup_ajaxsubmit(element, event_id) {
      $(element).ajaxSubmit({
         beforeSubmit: __beforeSubmit_form_validate,
         success: function(response) {
	    if (response.error) {
	       alert(response.error);
	       return;
	    }
            
	    if (!event_id && !SETTINGS.disable_sound && soundManager.enabled) {
                  soundManager.play('pling');
            }	    
            if (!event_id) {
               increment_total_no_events();
            }
	    
	    // close any open qtip
            close_current_tooltip();

            if (response.tags)
              $.each(response.tags, function(i, tag) {
                if ($.inArray(tag, AVAILABLE_TAGS) == -1)
                   AVAILABLE_TAGS.push(tag);
              });
	    
	    if (event_id)
	      $('#calendar').fullCalendar('removeEvents', event_id);

	    $('#calendar').fullCalendar('renderEvent', response.event);
	    var view = $('#calendar').fullCalendar('getView');
	    display_sidebar_stats_wrapped(view.start, view.end);
	    __update_described_colors();
	 }
      });
}

var _share_toggles = {};
function __hide_share(share) {
   if (_share_toggles[share.className]) {
      $('li.' + share.className, '#current-sharers').fadeTo(300, 0.4);
      $('div.' + share.className, '#calendar').fadeOut(300);
      _share_toggles[share.className] = false;
      SETTINGS.hidden_shares.push(share);
   } else {
      $('li.' + share.className, '#current-sharers').fadeTo(300, 1.0);
      $('div.' + share.className, '#calendar').fadeIn(300);
      _share_toggles[share.className] = true;
      SETTINGS.hidden_shares = $.grep(SETTINGS.hidden_shares, function(element) {
         return element != share;
      });
     
   }
   $.post('/share/', {key:share.key});
   return _share_toggles[share.className];
}

/* In a "share" we can expect there to be a name,
 * a className and a key so that that particular share can be hidden
 */
var colors = '#5C8D87,#994499,#6633CC,#B08B59,#DD4477,#22AA99,#668CB3,#DD5511,#D6AE00,#668CD9,#3640AD'.split(',');
var described_classNames = new Array();
var described_colors = {};
function __display_current_sharers(sharers) {
   var container = $('#current-sharers ul');
   var any = false;
   $.each(sharers, function(i, share) {

      var className = share.className;
      var is_new = false;
      if ($.inArray(className, described_classNames) == -1) {
	 is_new = true;
	 described_classNames.push(className);
      }
      var color = colors[$.inArray(className, described_classNames)];
      
      if (is_new) {
	 _share_toggles[share.className] = true;
	 container.append($('<li></li>')
			  .addClass(className)
			  .css('background-color', color)
			  .append($('<a href="#"></a>')
				  .text('hide')
				  .addClass('share-hider')
				  .bind('click', function() {
				     if (__hide_share(share))
				       $(this).text('hide');
				     else
				       $(this).text('show');
					
				     return false;
				  }))
			  .append($('<a href="#"></a>')
				  .text(share.full_name)));
      }

      described_colors[className] = color;
      any = true;
   });
   
   if (any) {
      __update_described_colors();
      if (SETTINGS.hidden_shares) {
         $.each(SETTINGS.hidden_shares, function(i, share) {
            _share_toggles[share.className] = false;
            $('li.' + share.className, '#current-sharers').fadeTo(0, 0.4);
            $('div.' + share.className, '#calendar').fadeOut(0);
            $('li.' + share.className + ' a.share-hider', '#current-sharers').text('show');
         });
      }
      
      $('#current-sharers').show();
   }
}

function __update_described_colors() {
   $.each(described_colors, function(className, color) {
      $('.' + className + ', .fc-agenda .' + className + ' .fc-event-time, .' + className + ' a'
	  ).css('background-color', color).css('border-color', color);
      if (!_share_toggles[className]) 
	$('div.' + className, '#calendar').fadeOut(0);
   });
}

function close_current_tooltip(parent) {
   if (current_tooltip) {
      current_tooltip.qtip().destroy();
      current_tooltip = null;
   }
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
                if ($.inArray(tag, AVAILABLE_TAGS) == -1)
                  AVAILABLE_TAGS.push(tag);
             });
           //if (response.hidden_shares)
           //  $.each(response.hidden_shares, function(i, share) {
           //     _share_toggles[share.className] = true;
           //     $('li.' + share.className, '#current-sharers').fadeTo(300, 0.4);
           //     
           //  });
             
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
      timeFormat: 'h(:mm)tt',
      defaultView: defaultView,
      editable: true,
      aspectRatio: 1.65, // 1.35 is default
      firstDay: SETTINGS.monday_first ? 1 : 0,
      weekends: !SETTINGS.hide_weekend,
      eventClick: _event_clicked,
      dayClick: _day_clicked,
      eventResize: _event_resized,
      eventDrop: _event_dropped,
      viewDisplay: function(view) {
         close_current_tooltip(); // if any open
	 display_sidebar_stats_wrapped(view.start, view.end);
         var href = '#' + view.name.replace('agenda', '').toLowerCase();
         href += ',' + view.start.getFullYear();
         href += ',' + (view.start.getMonth() + 1);
         href += ',' + view.start.getDate();
         location.href = href;
	 
      },
      windowResize: function(view) {
         __update_described_colors();
      }
   });
   
   $('input.cancel').live('click', function() {
      close_current_tooltip(this);
   });
   
   // Sooner or later we're going to need the qip
   /*
   $.getScript(JS_URLS.qtip, function() {
      __craigs_tip();
      return;
      	 L("Setting up qTip");
      $('.fc-view td').css('border', '1px solid red').css('background-color','#efefef');
	 $('.fc-view td').qtip({
            content:$('#add-form-container form')
	 });
   });
    */

});


// Because this file is loaded before stats.js
// We can't yet use display_sidebar_stats() since that function might not yet
// have been created. So until then we will use a function to avoid a
// 'display_sidebar_stats is not defined' error
display_sidebar_stats_wrapped = function(start, end) {
   if (typeof jqplot_loaded != 'undefined' && jqplot_loaded)
     display_sidebar_stats(start, end);

};
