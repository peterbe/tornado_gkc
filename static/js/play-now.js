var PlayNow = (function() {
  var delay_interval;
  function check(username, callback) {
    $.getJSON('/play/start/check_username.json',
              {username:username},
              function(response) {
      if (response.taken) {
        err("Sorry, username taken");
      } else if (response.username) {
        if (callback) {
          callback(response.username);
        } else {
          $('#play-now-username').val(response.username);
        }
      }
    });
  }

  function err(msg) {
    $('.play-now .error').text(msg);
  }

  return {
     start: function() {
       $('.play-now a').hide();
       $('.play-now p.note').hide();
       $('.play-now .error').css('color', 'red');
       $('.play-now form')
         .submit(function() {
           var username = $.trim($('#play-now-username').val());
           if (username) {
             check(username, function(username) {
               $('.play-now form').unbind('submit').submit();
             });
           } else {
             err("Uh? No username?");
             clearTimeout(delay_interval);
           }
           return false;
         })
           .show();
       $('#play-now-username').focus();

       delay_interval = setTimeout(function() {
         if (!$('#play-now-username').val()) {
           check($('#play-now-username').val());
         }
       }, 3 * 1000);
     }
  }
})();

head.ready(function() {
  $('.play-now a').click(function() {
    PlayNow.start();
  });

});
