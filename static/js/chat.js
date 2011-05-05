head.ready(function() {
   var s = new io.Socket(window.location.hostname, {port: 8001, rememberTransport: false});
   s.connect();

   s.addEvent('connect', function() {
      s.send('New participant joined');
   });

   s.addEvent('message', function(data) {
      var now = new Date();
      var t = now.getHours() + ':' + now.getMinutes();
      $('<div>', {text: t})
        .addClass('ts')
          .appendTo($('#chat'));
      var line = $('<div>');
      if (data.u) {
         $('<span>', {text: data.u + ':'})
           .addClass('u')
             .appendTo(line);
      }
      $('<span>', {text: data.m}).appendTo(line);
      line.appendTo($('#chat'));
   });

   //send the message when submit is clicked
   $('#chatform').submit(function (evt) {
      var line = $('#chatform [type=text]').val();
      $('#chatform [type=text]').val('');
      s.send(line);
      return false;
   });
});
