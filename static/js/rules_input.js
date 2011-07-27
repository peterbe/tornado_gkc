head.ready(function() {
  $('input[type="number"]').bind('keyup', function() {
    $(this).val($(this).val().replace(/[^\d]+/, ''));
  });
});
