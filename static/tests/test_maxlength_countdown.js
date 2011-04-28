function assert(well, msg) {
   msg = msg === undefined ? "" : msg;
   if (!well) throw new Error(msg);
}
$(function() {
   
   // prevent browser defaults
   $('#id_foo').val(''); 
   $('#id_foo2').val('P');
   $('#id_bar').val('already some stuff');
   
   $('input[maxlength]').not('#id_bar').maxlength_countdown();
   
   assert($('#wrap-foo span.maxlength-countdown').size(), 'no span.maxlength-countdown');
   var mc = $('#wrap-foo span.maxlength-countdown');
   assert(mc.size() == 1, 'more than one');
   assert(mc.css('opacity') == 0);
   assert('0 of max 10' == mc.text(), mc.text());
   
   $('#id_bar').maxlength_countdown(function(count, max) {
      return count + ' OF ' + max;
   });
   mc = $('#wrap-bar span.maxlength-countdown');
   assert(mc.size() == 1, 'more than one');
   assert(mc.css('opacity') > 0 && mc.css('opacity') < 1);
   assert('18 OF 100' == mc.text(), mc.text());
   assert(!$('#wrap-not span.maxlength-countdown').size());
   
   $('#id_foo').val('xxxxxxxxxx').trigger('keyup');
   mc = $('#wrap-foo span.maxlength-countdown');
   assert('10 of max 10' == mc.text(), mc.text());
   assert($('#wrap-foo span.maxlength-maxed').size());

});