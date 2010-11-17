   
if ($('#close-sharing-open-account').size()) {
   $('#close-sharing-open-account').click(function() {
      $('a.account').click();
      return false;
   });
} else {
   if ($('#share_url').size()) {
      $('#share_url')[0].focus();
      $('#share_url')[0].select();
   }
}

$('a.more-options').click(function() {
   if ($('#more-options:visible').size()) {
      $('#more-options').hide();
      $(this).text("more options");
   } else {
      $('#more-options').show();
      $(this).text("hide options");
   }
   return false;
});

function __check(tag, toggle) {
   $('select[name="tags"] option').each(function(i, e) {
     if ($(e).val() == tag) {
        $(e).attr('selected', toggle);
     }
   });
}

function _check_option(tag) {
   __check(tag, true);
}
function _uncheck_option(tag) {
   __check(tag, false);
}

$('#tags-chosen').droppable({
   activeClass: 'ui-state-default',
   hoverClass: 'ui-state-hover',
   drop: function(event, ui) {
      $(this).find('.placeholder').remove();
      var tag_text = ui.draggable.text();
      _check_option(tag_text);
      $('<span></span>').text(tag_text).appendTo($('<li></li>').addClass('tag').appendTo($('ul', this)).draggable({
         revert:'invalid'
      }));
      ui.draggable.remove();
      _save_share_tags();
   }
});

$('#tags-available li.tag, #tags-chosen li.tag').draggable({
   revert: 'invalid'
});

$('#tags-available').droppable({
   drop: function(event, ui) {
      var tag_text = ui.draggable.text();
      _uncheck_option(tag_text);
      $('<span></span>').text(tag_text).appendTo($('<li></li>').addClass('tag').appendTo($('ul', this)).draggable({
         revert:'invalid'
      }));
      // here, reorder the UL?
      ui.draggable.remove();
      _save_share_tags();
   }
});


function _save_share_tags() {
   $('#save-note').show().text("saving");
   $('form#share').ajaxSubmit({
      success: function(response) {
         setTimeout(function() {
            $('#save-note').text("saved!");
            setTimeout(function() {
               $('#save-note').fadeOut('fast');
            }, 2*1000);
         }, 1000);
      }
   });
}

if ($('select[name="tags"] option:selected').size()) {
   $('a.more-options').click();
}