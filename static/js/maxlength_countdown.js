(function($) {
   $.fn.maxlength_countdown = function(formatter) {
      formatter = formatter !== undefined ? formatter : function(c, m) {
	 return c + ' of max ' + m;
      };
      return this.each(function() {
	 var e = $(this);
	 if (!e.attr('id')) {
	    throw "input element lacks ID attribute";
	 }
	 var c = e.val().length;
	 var p = c / parseFloat($(this).attr('maxlength'));
	 var t = $('<span>',
		   //{text: c + ' of max ' + $(this).attr('maxlength')})
		   {text: formatter(c, $(this).attr('maxlength'))})
	   .attr('id', 'countdown' + e.attr('id'))
	     .fadeTo(0, p)
	       .addClass('maxlength-countdown')
		 .insertAfter(e);
	 if (p >= 1) {
	    t.addClass('maxlength-maxed');
	 }
	 e.bind('keyup', function() {
	    var e = $(this);
	    var c = e.val().length;
	    var t = $('#countdown' + e.attr('id'));
	    var p = c / parseFloat(e.attr('maxlength'));
	    t.text(formatter(c, e.attr('maxlength')))
	      .fadeTo(100, p);
	    if (p >= 1) {
	       t.addClass('maxlength-maxed');
	    } else {
	       t.removeClass('maxlength-maxed');
	    }
	 }).bind('blur', function() {
	    var e = $(this);
	    var c = e.val().length;
	    var p = c / parseFloat(e.attr('maxlength'));
	    if (p > 0)
	      $('#countdown' + e.attr('id'))
		.fadeTo(500, Math.min(0.2, p));
	 });
      });
   };
})(jQuery);