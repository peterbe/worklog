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



function _setup_ajaxsubmit(element) {
   $.getScript(JS_URLS.jquery_form, function() {
      __inner_setup_ajaxsubmit(element);
   });
}

function __inner_setup_ajaxsubmit(element) {
   $(element).ajaxSubmit({
      //beforeSubmit: __beforeSubmit_form_validate,
      success: function(response) {
         if (response.error) {
            alert(response.error);
            return;
         }
         $.each(response.vote_weights, function(i, e) {
            var c = $('#' + e.id);
            $('span.vote_weight', c).text(e.weight);
         });
         // have to use $.param() because if I use data parameters to
         // .load() it will use action a POST.
         $('#feature--' + response.id).load('/feature-requests/feature.html?'+
                                            $.param({id:response.id}));
         close_current_tooltip();
      }
   });
}
                                  
function close_current_tooltip() {
   if (current_tooltip) {
      current_tooltip.qtip().destroy();
      current_tooltip = null;
   }
}

var current_tooltip;
function _setup_qtip(element) {
   var _id = $(element).parents('div.request').attr('id');
   $('#voteup-form-container input[name="id"]').val(_id);
   var qtip_options = {
      content: {
         text: $('#voteup-form-container').html()
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
            $('form.voteup').submit(function() {
               _setup_ajaxsubmit(this);
               return false;
            });
            $('input[name="comment"]:visible').focus();
         }
      }
   };
   current_tooltip = $(element);
   current_tooltip.qtip(qtip_options);
   bind_esc_key();  
}

$(function() {
   $.each(HAVE_VOTED, function(i, e) {
      $('p.voteup a', '#' + e).fadeTo(0, 0.3).attr('title', "You have already voted on this one");
   });
   
   var form = $('form[method="post"]');
   form.validate({
      rules: {
         title: {
            required: true,
            maxlength: 250, 
            messages: {
               required: "Required input"
            }
         }
      },
      keyup: false,
      success: function(label_) {
         if (label_.attr('for') == 'title') {
            var title = $('input[name="title"]').val();
            
            if (title.length && title != $('input[name="title"]').attr('title')) {
               $.getJSON('/feature-requests/find.json', {title:title}, function(response) {
                  if (response.feature_requests && response.feature_requests.length) {
                     $('label[for="title"]').text("Feature request already submitted");
                  }
               });
            }
         }
      }
   });

   form.submit(function() {
      // last check that the title isn't the default text
      var t = $('input[name="title"]', this);
      if (t.val() == t.attr('title')) {
         var error_message = "Please enter a brief and descriptive title";
         if ($('label.error[for="title"]').size()) {
            $('label.error[for="title"]').text(error_message);
         } else {
            alert(error_message);
         }
         return false;
      }
      return true;
   });
   
   $('input[name="title"], textarea', form).focus(function() {
      if ($(this).val() == $(this).attr('title')) {
         $(this).val('').removeClass('placeholdervalue');
      }
   }).blur(function() {
      if (!$.trim($(this).val())) {
         $(this).val($(this).attr('title')).addClass('placeholdervalue');
      }
   });
   
   var _keys = ['input[name="title"]', 'textarea']
   for (i in _keys) {
      var k = _keys[i];
      if (!$(k, form).val() || $(k, form).val() == $(k, form).attr('title')) {
         $(k, form).val($(k, form).attr('title')).addClass('placeholdervalue');
      }
   }
   
   $('.voteup a').click(function() {
      _setup_qtip(this);
      return false;
   });
   
   $('input.cancel').live('click', function() {
      close_current_tooltip(this);
   });
   
});