head.js(JS_URLS.fancybox, function() {

   $('#opener').fancybox({
      autoDimensions: false,
      width: 850,
      height: '90%',
      type: 'iframe',
      transitionIn: 'none',
      transitionOut: 'none',
      showCloseButton: false,
      enableEscapeButton: false,
      onClosed: function() {
         location.href = '/';
      }
   });
});
head.ready(function() {
   setTimeout(function() {
      $('#opener').trigger('click');
   }, 500);
});
