
head.ready(function() {
   var search_placeholder = 'Search';
   $('#search').submit(function() {
      var value = $('input[name="q"]', this).val();
      if (value == search_placeholder) value = '';
      if (!value) return false;
   });

   $('input[name="q"]', '#search')
     .focus(function() {
	if ($(this).val() == search_placeholder) {
	   $(this).val('').removeClass('placeholder');
	}
     })
       .blur(function() {
	  if (!$.trim($(this).val())) {
	     $(this).val(search_placeholder).addClass('placeholder');
	  }
       });

   if (!$('input[name="q"]', '#search').val()) {
      $('input[name="q"]', '#search').val(search_placeholder).addClass('placeholder');
   }


});
