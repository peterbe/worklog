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
});