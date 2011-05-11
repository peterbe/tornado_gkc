var Title = (function() {
   var current_title = document.title
     , original_title = document.title
     , no_participants = 0
     , timer;
   function render() {
      var word = no_participants == 1 ? 'participant' : 'participants';
      document.title = '(' + no_participants + ' ' + word + ') ' + original_title;
      current_title = document.title;
   }
   return {
      increment_participants: function (inc) {
	 no_participants += inc;
         L('timer', timer);
         render();
      },
      decrement_participants: function (dec) {
         if (inc < 0) throw "decrement with a positive number";
	 no_participants -= dec;
         if (!timer) {
            render();
         }
      },
      show_temporarily: function (msg, msec) {
         msec = typeof(msec) !== 'undefined' ? msec : 2000;
         if (timer) {
            clearTimeout(timer);
         }
         var old = current_title;
         document.title = msg;
         timer = setTimeout(function() {
            document.title = old;
         }, msec);
      }
   }
})();

var Chat = (function() {
   return {
      show_participants: function (participants) {
         $.each(participants, function (i, e) {
            Chat.show_participant(e, false);
         });
      },
      show_participant: function (participant, is_new) {
         var name = $('<li>', {text: participant})
           .click(function() {
              $('#chatform input[type="text"]').val(participant+': ').focus();
           })
           .appendTo($('#participants ul'));

         if (is_new)  {
            name.addClass('new');
            setTimeout(function() {
               $('#participants li.new').removeClass('new');
            }, 2*1000);
         }
      },
      remove_participant: function (participant) {
         $('#participants li').each(function() {
            if ($(this).text() == participant) {
               $(this).remove();
            }
         });
      },
      show_message: function (message, user, timestamp) {
         var now;
         now = new Date();
         if (timestamp) {
            now.setTime(timestamp*1000);
         }
         var h = now.getHours(), m = '' + now.getMinutes();
         if (m.length == 1) m = '0' + m;
         var t = now.getHours() + ':' + m;

         $('<div>', {text: t})
           .addClass('ts')
             .appendTo($('#chat'));
         var line = $('<div>');
         if (user) {
            $('<span>', {text: user + ':'})
              .addClass('u')
                .appendTo(line);
         } else {
            $('<span>', {text: 'system message:'})
              .addClass('system')
                .appendTo(line);
         }
         $('<span>', {text: message}).appendTo(line);
         line.appendTo($('#chat'));
	 $('#chat')[0].scrollTop = 1000000;
      }
   }
})();

head.ready(function() {
   var s = new io.Socket(window.location.hostname, {port: 9000, rememberTransport: false});
   s.connect();

   s.addEvent('connect', function() {
      $('#chat-wrapper').fadeIn(700);
      $('#pleasewait').fadeOut(100);
      setTimeout(function() {
         $('#chatform input[type="text"]').focus();
      }, 400);
      //s.send('joined');
   });

   s.addEvent('message', function(data) {
      if (data.m) {
         // data.u might be null
         Chat.show_message(data.m, data.u, data.t);
      }
      if (data.p) {
         Chat.show_participant(data.p, true);
	 Title.increment_participants(1);
      }
      if (data.ps) {
         Chat.show_participants(data.ps);
	 Title.increment_participants(data.ps.length);
      }
      if (data.po) {
         Chat.remove_participant(data.po);
	 Title.decrement_participants(1);
      }
      if (data.error) {
         alert(data.error);
      }
   });

   //send the message when submit is clicked
   $('#chatform').submit(function (evt) {
      var line = $('#chatform [type=text]').val();
      $('#chatform [type=text]').val('');
      s.send(line);
      return false;
   });
});
