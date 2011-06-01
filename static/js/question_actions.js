head.ready(function() {
   $('form#reject').submit(function() {
      if ($('#reject_comment:hidden').size()) {
         $('#reject_comment').show();
         $('#reject_comment textarea').trigger('focus');
         return false;
      }
   });
   $('form#comment').submit(function() {
      if ($('#send_comment:hidden').size()) {
         $('#send_comment').show();
         $('#send_comment textarea').trigger('focus');
         return false;
      } else if (!$.trim($('#send_comment textarea').val()).length) {
         return false;
      }
   });
});
