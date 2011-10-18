/* SHARING
 */
var Sharing = (function() {
   var described_classNames = new Array()
     , described_colors = {}
   ,  _share_toggles = {};

   function hide_share(share) {
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
      $.post('/share/', {_xsrf:XSRF, key: share.key});
      return _share_toggles[share.className];
   }

   return {
      hide_hidden: function() {
         $.each(_share_toggles, function (className, show) {
            if (!show) {
               $('div.' + className, '#calendar').hide();
            }
         });
      },
      display_current_sharers: function(sharers) {
         var container = $('#current-sharers ul');
         var any = false;
         var color;
         $.each(sharers, function(i, share) {
            var className = share.className;
            var is_new = false;
            if ($.inArray(className, described_classNames) == -1) {
               is_new = true;
               described_classNames.push(className);
            }
            //var color = colors[$.inArray(className, described_classNames)];
            color = share.color;

            if (is_new) {
               _share_toggles[share.className] = true;
               container.append($('<li></li>')
                                .addClass(className)
                                .css('background-color', color)
                                .append($('<a href="#"></a>')
                                        .text('hide')
                                        .addClass('share-hider')
                                        .bind('click', function() {
                                           if (hide_share(share)) {
                                              $(this).text('hide');
                                           } else {
                                              $(this).text('show');
                                           }
                                           return false;
                                        }))
                                .append($('<a href="#"></a>')
                                        .text(share.full_name)));
            }

            described_colors[className] = color;
            any = true;
         });
         if (any) {
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
   }
})();



function __standard_qtip_options() {
  return {
   show: {
      when: 'click',
      ready: true,
      solo: true
   },
   hide: 'unfocus'

  };
}

var g_origKeyUp;
function unbind_esc_key() {
  document.onkeyup = g_origKeyUp;
}

function bind_esc_key() {
  function handleOnkeyup(e){
    var evtobj=window.event? event : e;
    var unicode=evtobj.charCode? evtobj.charCode : evtobj.keyCode;

    // Close bookmarklet on Escape
    if (unicode == 27){
      close_current_tooltip();
      unbind_esc_key();
    }
  }

  // Preserve original onkeyup handler
  g_origKeyUp = document.onkeyup;

  // Substitute new onkeyup
  document.onkeyup = handleOnkeyup;
}

var current_tooltip;
function _day_clicked(date, allDay, jsEvent, view) {
   var url = '/events';
   // need to set date and allDay into $('#add-form-container form')
   $('#add-form-container form').attr('action', url);
   if (allDay) {
     $('#add-form-container input[name="all_day"]').val('1');
   } else {
     $('#add-form-container input[name="all_day"]').val('');
   }
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
          target: this
      },
      hide: {
         event: false
      },
      show: {
           solo: true,
           ready: true,
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
              _setup_ajaxsubmit(this);
              return false;
           });
	   __setup_tag_autocomplete($('input[name="title"]:visible'));
	   $('input[name="title"]:visible').focus();
        }
      }
   };
   //qtip_options = $.extend(qtip_options, __standard_qtip_options());
   current_tooltip = $(this);
   current_tooltip.qtip(qtip_options);
   bind_esc_key();
  if (!SETTINGS.disable_sound)
    preload_sound('add');
}

function _event_clicked(event, jsEvent, view) {
  // by default events don't have the 'editable' attribute. It's usually only
  // set when the event is explcitely *not* editable.
  var is_editable = true;
  if (typeof event.editable != 'undefined') {
    is_editable = event.editable;
  }

  if (is_editable) {
    var url = '/event.json?id=' + event.id;
  } else {
    var url = '/event.html?id=' + event.id;
  }
  function _prepare_edit_event(container) {
    $('form', container).submit(function() {
      _setup_ajaxsubmit(this, event.id);
      return false;
    });
    if ($('input[name="title"]', container).size()) {
      __setup_tag_autocomplete($('input[name="title"]', container));
      $('input[name="title"]', container).focus();
    } else {
      // it hasn't been loaded yet :(
      setTimeout(function() {
        __setup_tag_autocomplete($('input[name="title"]', container));
        $('input[name="title"]', container).focus();
      }, 500);
    }

    if (!$('input[name="external_url"]', container).val()) {
      $('input[name="external_url"]', container)
        .addClass('placeholdervalue')
          .val($('input[name="placeholdervalue_external_url"]', container).val());
    }

    $('a.more-editing', container).click(function() {
      if ($('div.more-editing:visible', container).length) {
        $('div.more-editing', container).hide();
        $(this).text('More options?');
      } else {
        $('div.more-editing', container).show();
        $(this).text('Less options?');
      }
      return false;
    });

    $('a.delete', container).click(function() {
      close_current_tooltip();
      $.post('/event/delete/', {_xsrf:XSRF, id: event.id}, function() {
        decrement_total_no_events();
        $('#calendar').fullCalendar('removeEvents', event.id);
        var view = $('#calendar').fullCalendar('getView');
        Calendar.display_sidebar_stats(view);
        Sharing.hide_hidden();
        show_undo_delete("UNDO last delete", event.id);
      });
      play_sound('delete');
      return false;
    });
  }

  /* This function is called when the qtip has opened for previewing */
  function _prepare_preview_event() {

  }

  var qtip_options = {
     content: {
        ajax: {
           url: url,
            success: function(data, status) {
              if (is_editable) {
                var clone = $('#edit-form-container').clone();
                $('input[name="title"]', clone).val(data.title);
                $('input[name="id"]', clone).val(data.id);
                if (data.external_url) {
                  $('input[name="external_url"]', clone).val(data.external_url);
                } else {
                  $('input[name="external_url"]', clone)
                    .addClass('placeholdervalue')
                      .val($('input[name="placeholdervalue_external_url"]', clone).val());
                }
                if (data.description) {
                  $('textarea[name="description"]', clone).val(data.description);
                } else {
                  $('textarea[name="description"]', clone)
                    .addClass('placeholdervalue')
                      .val($('input[name="placeholdervalue_description"]', clone).val());
                }
                // reason for this:
                // http://craigsworks.com/projects/forums/thread-can-t-remove-the-word-loading-with-this-set-content-text
                this.set('content.text', '&nbsp;');
                _prepare_edit_event(clone);
                this.set('content.text', clone);

                // doing this after because a.more-editing is not visible until it's
                // gone into the qtip
                if (data.description || data.external_url) {
                  $('a.more-editing').click();
                }

              } else {
                this.set('content.text', data);
              }
              return false;
            }
        }
     },
    position: {
       my: 'bottom middle',
        at: 'center',
        target: this
    },
    hide: {
       event: false
    },
    show: {
       solo: true,
        ready: true,
        event: 'click'
    },
    style: {
       classes: 'ui-tooltip-shadow',
        tip: {
           corner: 'middle bottom'
        }
    }
  };
  //qtip_options = $.extend(qtip_options, __standard_qtip_options());
  current_tooltip = $(this);
  current_tooltip.qtip(qtip_options);
  bind_esc_key();
  if (!SETTINGS.disable_sound)
    preload_sound('delete');
}

function _event_resized(event,dayDelta,minuteDelta,revertFunc, jsEvent, ui, view) {
   $.post('/event/resize/', {_xsrf:XSRF, days: dayDelta, minutes: minuteDelta, id: event.id}, function(response) {
      if (response.error) {
         alert(response.error);
         revertFunc();
      }
      Calendar.display_sidebar_stats(view);
      Sharing.hide_hidden();
   });
}

function _event_dropped(event,dayDelta,minuteDelta,allDay,revertFunc, jsEvent, ui, view) {
   var date_before = new Date(event.start.getTime() - dayDelta*24*3600*1000);
   $.post('/event/move/', {_xsrf:XSRF, all_day: allDay, days: dayDelta, minutes: minuteDelta, id: event.id}, function(response) {
      if (response.error) {
         alert(response.error);
         revertFunc();
      }

      if (date_before.getMonth() != event.start.getMonth()) {
         // it can happen that the event is moved from one month
         // to another (e.g. 30th Nov to 1st Dec). If this happens re-render
         // the pie chart stats
         Calendar.display_sidebar_stats(view);
      }
      Sharing.hide_hidden();
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
	   return row[0];
	}
   });
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
      if (!event_id) {
         increment_total_no_events();
      }

      // close any open qtip
      close_current_tooltip();

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

	    if (!event_id && !SETTINGS.disable_sound) {
        play_sound('add');
      }
      if (!event_id) {
        increment_total_no_events();

        if ($('#introduction-video, #introduction-video-after').size()) {
          $('#introduction-video:visible').hide('slow');
          $('#introduction-video-after:visible').hide('slow');
          if ($('#report-link:hidden').size()) {
            $('#report-link').show('slow');
          }
        }
      }

	    // close any open qtip
      close_current_tooltip();

      if (response.tags) {
        $.each(response.tags, function(i, tag) {
          if ($.inArray(tag, AVAILABLE_TAGS) == -1)
            AVAILABLE_TAGS.push(tag);
        });
      }

	    if (event_id)
	      $('#calendar').fullCalendar('removeEvents', event_id);

	    $('#calendar').fullCalendar('renderEvent', response.event);
	    var view = $('#calendar').fullCalendar('getView');
      Calendar.display_sidebar_stats(view);
      Sharing.hide_hidden();
    }
  });
}

var undo_delete_timer;
function show_undo_delete(text, event_id) {
   if (undo_delete_timer) {
      clearTimeout(undo_delete_timer);
   }
   $('#undo-delete a').remove();
   $('#undo-delete:hidden').show();
   $('#undo-delete')
     .append($('<a href="#"></a>').text(text).click(function() {
        $.post('/event/undodelete/', {_xsrf:XSRF, id:event_id}, function(response) {
           if (!SETTINGS.disable_sound) {
              play_sound('add');
           }
           increment_total_no_events();
           $('#calendar').fullCalendar('renderEvent', response.event);
           var view = $('#calendar').fullCalendar('getView');
           Calendar.display_sidebar_stats(view);
           Sharing.hide_hidden();
           $('#undo-delete').hide();
        });
        return false;
     }));

   undo_delete_timer = setTimeout(function() {
      $('#undo-delete:visible').fadeOut(800);
   }, 5 * 1000);
}

function close_current_tooltip(parent) {
   if (current_tooltip) {
      current_tooltip.qtip().destroy();
      current_tooltip = null;
   }
}

var AVAILABLE_TAGS;

var Calendar = (function() {
   var _first_view_display = false;
   // private
   function _load_calendar() {
      var defaultView = 'month';
      // By default we assume that we should save this view in a cookie. The only
      // reason not to do it later is if we've just loaded it from a cookie.
      var save_view_cookie = true;
      if (location.hash.search('#week') == 0) {
        defaultView = 'agendaWeek';
      } else if (location.hash.search('#day') == 0) {
         defaultView = 'agendaDay';
      }
      var today = new Date();
      var year = today.getFullYear();
      var month = today.getMonth();
      var day = undefined;

      var _lastview_cookie = $.cookie('lastview');
      var hash_code_regex = /(\d{4}),(\d{1,2}),(\d{1,2})/;
      if (hash_code_regex.test(location.hash)) {
         var _match = location.hash.match(hash_code_regex);
         year = parseInt(_match[1]);
         month = parseInt(_match[2]) - 1;
         day = parseInt(_match[3]);
      } else if (_lastview_cookie && hash_code_regex.test(_lastview_cookie)) {
         if (_lastview_cookie.search('#week') == 0) {
            defaultView = 'agendaWeek';
         } else if (_lastview_cookie.search('#day') == 0) {
            defaultView = 'agendaDay';
         }
         var _match = _lastview_cookie.match(hash_code_regex);
         year = parseInt(_match[1]);
         month = parseInt(_match[2]) - 1;
         day = parseInt(_match[3]);
         // if we've just loaded it from the cookie we don't need to save the
         // cookie again.
         save_view_cookie = false;
      }

      $('#calendar').fullCalendar({
         events: function(start, end, callback) {
            var url = '/events.json';//?start=' + start.getTime() + '&end=' + end.getTime();
            var ops = {start: start.getTime(), end: end.getTime()};
            if (SETTINGS.hidden_shares == undefined) {
               ops.include_hidden_shares = 'true';
               SETTINGS.hidden_shares = [];
            } else {
               // we've already downloaded all tags
               ops.include_hidden_shares = '';
            }

            if ('undefined' === typeof AVAILABLE_TAGS) {
               ops.include_tags = 'all';
               AVAILABLE_TAGS = [];
            } else {
               // we've already downloaded all tags
               ops.include_tags = 'none';
            }
            $.getJSON(url, ops, function(response) {
               callback(response.events);
               if (response.hidden_shares) {
                  SETTINGS.hidden_shares = response.hidden_shares;
               }
               if (response.sharers) {
                  Sharing.display_current_sharers(response.sharers);
               }
               if (response.tags) {
                  $.each(response.tags, function(i, tag) {
                     if ($.inArray(tag, AVAILABLE_TAGS) == -1)
                       AVAILABLE_TAGS.push(tag);
                  });
               }
               if (response.events.length) {
                  if ($('#introduction-video').size()) {
                     $('#introduction-video').hide('slow');
                     if ($('#report-link:hidden').size()) {
                        $('#report-link').show('slow');
                     }
                  }
               }
               /*
                * Doesnt work becuase qtip doesn't work when I try to set up the options.
               if (location.hash) {
                  var _match = location.hash.match(/[a-f0-9]{24}/);
                  L(_match[0]);
                  var _events = $('#calendar').fullCalendar('clientEvents', _match[0]);
                  if (1 == _events.length) {
                     _event_clicked(_events[0], null, $('#calendar').fullCalendar('getView'));
                  }
               }*/

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
         //timeFormat: 'h(:mm)tt',
         timeFormat: SETTINGS.ampm_format ? 'h(:mm)tt' : 'H:mm',
         axisFormat: SETTINGS.ampm_format ? 'h(:mm)tt' : 'H:mm',
         firstHour: SETTINGS.first_hour,
         slotMinutes: 30, // setting?
         defaultView: defaultView,
         editable: true,
         aspectRatio: 1.35, // 1.35 is default
         firstDay: SETTINGS.monday_first ? 1 : 0,
         weekends: !SETTINGS.hide_weekend,
         weekMode: 'variable',
         eventClick: _event_clicked,
         dayClick: _day_clicked,
         eventResize: _event_resized,
         eventDrop: _event_dropped,
         viewDisplay: function(view) {
            Sharing.hide_hidden();
            close_current_tooltip(); // if any open
            // viewDisplay() is called(back) the first time you render the
            // calendar but also every time you change the view (month,week,day)
            // but we only want to update the sidebar stats when the view is
            // *changed*
            if (!_first_view_display) {
               _first_view_display = true;
            } else {
               Calendar.display_sidebar_stats(view);
            }
            if (save_view_cookie) {
               var href = '#' + view.name.replace('agenda', '').toLowerCase();
               href += ',' + view.start.getFullYear();
               href += ',' + (view.start.getMonth() + 1);
               href += ',' + view.start.getDate();
               $.cookie('lastview', href, {expires: 5});
            } else {
               save_view_cookie = true;
            }

         },
         windowResize: function(view) {
            Sharing.hide_hidden();
         }
      });
   }



   // public
   return {
      load: function() {
         _load_calendar();
         /*$.getJSON('/xsrf.json', function(r) {
            XSRF = r.xsrf;
         });*/
      },
      display_sidebar_stats: function(view) {
         // the global 'display_sidebar_stats' here is a function
         // defined in sidebar.js
         if ('undefined' != typeof display_sidebar_stats) {
            display_sidebar_stats(view.start, view.end);
         }
      }
   }
})();



head.ready(function() {
   $('input.cancel').live('click', function() {
      close_current_tooltip(this);
   });
   $('input.placeholdervalue, textarea.placeholdervalue').live('focus', function() {
      var placeholdervalue_text = $('input[name="placeholdervalue_'+$(this).attr('name') + '"]').val();
      if ($(this).val() == placeholdervalue_text) {
         $(this).val('').removeClass('placeholdervalue');
      }
      $(this).blur(function() {
         var placeholdervalue_text = $('input[name="placeholdervalue_'+$(this).attr('name') + '"]').val();
         if ($.trim($(this).val())) {
            if ($(this).attr('name') == 'external_url' && $(this).val().search('://') == -1)
              $(this).val('http://' + $(this).val());
         } else {
            $(this).addClass('placeholdervalue').val(placeholdervalue_text);
         }
      });
   });
});
