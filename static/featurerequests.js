

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
   //bind_esc_key();  
}

$(function() {
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
});