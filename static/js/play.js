var L = function() {
   if (window.console && window.console.log)
     console.log.apply(console, arguments);
};

function message(obj){
   var el = document.createElement('p');
   if ('announcement' in obj) el.innerHTML = '<em>' + esc(obj.announcement) + '</em>';
   else if ('message' in obj) el.innerHTML = '<b>' + esc(obj.message[0]) + ':</b> ' + esc(obj.message[1]);
   document.getElementById('chat').appendChild(el);
   document.getElementById('chat').scrollTop = 1000000;
}

function send(){
   var val = document.getElementById('text').value;
   socket.send(val);
   message({ message: ['you', val] });
   document.getElementById('text').value = '';
}

function esc(msg){
   return msg.replace(/</g, '&lt;').replace(/>/g, '&gt;');
};

var Clock = (function () {
   var _clock
     , _callback
     , _init_seconds;
   return {
      stop: function () {
	 clearTimeout(_clock);
      },
      start: function (seconds, callback) {
	 Rumbler.stop();
	 _init_seconds = seconds;
	 Clock.tick(seconds);
	 _callback = callback;
      },
      tick: function (seconds) {
	 $('#timer').text(seconds);
	 if (seconds > 0) {
	    _clock = setTimeout(function() {
	       Clock.tick(seconds - 1);
	    }, 1000);
	    var p = parseInt(100 * seconds / _init_seconds);
	    // p is percentage of time left
	    // max rumble speed is 200 (quite arbitrary)
	    var rumbleSpeed;
	    if (p < 30) {
	       rumbleSpeed = 1 * p;
	       var range;
	       if      (p < 1) range = 6;
	       else if (p < 5) range = 4;
	       else if (p < 10) range = 3;
	       else    range = 2;
	       Rumbler.start($('#timer'), rumbleSpeed, range)
	    }
	 } else {
	    _callback();
	 }
      }
   }
})();


var question_handler = (function() {
   var _current_question
     , _initialized = false
     , _timer_callback
     , _has_answered = false;

   return {
      initialize: function() {
         L("initializing");
	 $('#respond').show();
	 $('#waiting').hide();
	 $('#your_name').hide();
	 _initialized = true;
      },
      load_question: function(question) {
         L("LOAD_QUESTION", question);
	 if (!_initialized) {
	    this.initialize();
	 }
	 _has_answered = false;
	 _current_question = question;
	 $('#timer:hidden').show(100);
	 $('#input:hidden').show();
	 $('#alternatives input.alternative').remove();
	 $('#alternatives-outer:visible').hide();
	 $('#load-alternatives:hidden').show();
	 $('#typed:hidden').show();
	 $('#answer').removeAttr('readonly').removeAttr('disabled').val('');
	 $('#question li.current').removeClass('current').addClass('past');
	 $('#question').append($('<li>', {id: question.id}
				).addClass('current')
			      .append($('<span>', {text: question.text})));
	 $('#alternatives').fadeTo(0, 1.0);
	 $('#alert:visible').hide(400);
	 Clock.stop();
	 Clock.start(15, this.timed_out);
	 L("focus on answer");
	 $('#answer').focus();

	 // check if an image was loaded to the previous question
	 if (!$('img', $('li.past').eq(-1)).size()) {
	    $('li.past').eq(-1)
	      .append($('<img>', {src:'/images/hourglass.png',
		alt:'Timed out'
	      }));
	 }
      },
      timed_out: function() {
	 $('#question li.current').addClass('past');
	 $('#answer').removeAttr('readonly');
	 var msg = "Both too slow";
	 $('li.current')
	   .append($('<img>', {src:'/images/hourglass.png',
		alt:msg
	   }));
	 $('#input').hide();
	 $('#alert').text(msg).show(100);
	 $('#timer').hide(100);
	 socket.send({timed_out:true});
      },
      finish: function(you_won, draw) {
	 $('#input').hide();
	 question_handler.stop();
	 draw = draw || false;
	 $('#question li.current').removeClass('current').addClass('past');
	 if (draw) {
	    $('#you_drew').show()
	      .append($('<a>', {
		 href:CONFIG.HOMEPAGE_URL,
		   text:"Go back to the home page"}));

	 } else {
	    if (you_won) {
	       $('#you_won').show()
		 .append($('<a>', {
		    target: '_top',
		 href: CONFIG.HIGHSCORE_URL,
		      text:"Check out where you are now on the Highscore list"}));

	    } else {
	       $('#you_lost').show()
		 .append($('<a>', {
		    target: '_top',
		    href: CONFIG.HOMEPAGE_URL,
		      text:"Go back to the home page"}));
	    }
	 }
      },
      stop: function(information) { // the whole battle is over
	 Clock.stop();
	 //$('#question li.current').removeClass('current').addClass('past');
	 $('#timer').hide();
	 //$('form#respond').fadeTo(900, 0.4);
	 $('#input').hide(800);
	 if (information && information.message) {
	    $('#information p').text(information.message);
	    $('#information').show();
	 }
      },
      right_answer: function() {
	 var msg = 'Yay! you got it right';
	 $('li.current')
	   .append($('<img>', {src:'/images/right.png',
		alt:msg
	   }));
	 $('#alert').text(msg).show(100);
      },
      wrong_answer: function() {
	 var msg = 'Sorry. You got it wrong';
	 $('li.current')
	   .append($('<img>', {src:'/images/wrong.png',
		alt:msg
	   }));
	 $('#alert').text(msg).show(100);
      },
      too_slow: function() {
	 var msg = 'Sorry. You were too slow';
	 $('li.current')
	   .append($('<img>', {src:'/images/wrong.png',
		alt:msg
	   }));
	 $('#alert').text(msg).show(100);
      },

      send_answer: function(answer) {
	 $('#answer').attr('readonly','readonly').attr('disabled','disabled');
	 socket.send({answer:answer});
	 _has_answered = true;
      },
      has_sent_answer: function() {
	 return _has_answered;
      }
   }
})();

var alternatives = (function() {
   return {
      load: function() {
	 $('#load-alternatives').hide();
	 socket.send({alternatives:true});
      },
      show: function(alts) {
	 var container = $('#alternatives');
	 for (var i in alts) {
	    container.append($('<input>', {name:'alternative', type:'button', value:alts[i]})
			     .addClass('alternative')
			     .click(function() {
				alternatives.answer(this.value);
			     }));
	 }
	 $('#alternatives-outer').show();
	 $('#typed:visible').hide();
      },
      answer: function(ans) {
	 socket.send({answer:ans});
	 $('#alternatives input.alternative')
	   .attr('readonly','readonly')
	     .attr('disable','disable')
	       .unbind('click');
	 $('#alternatives').fadeTo(300, 0.4);
      }
   }
})();

function __log_message(msg) {
   var el = document.createElement('p');
   var d = new Date();
   var line = '<em>' + d.getHours() + ':' + d.getMinutes() + ':' + d.getSeconds() + '.' + d.getMilliseconds() + '</em> ';
   if ('object' == typeof msg) {
      line += JSON.stringify(msg);
   } else {
      line += msg;
   }
   el.innerHTML = line;
   document.getElementById('log').appendChild(el);
   document.getElementById('log').scrollTop = 1000000;
}

var socket = new io.Socket(null, {port: CONFIG.SOCKET_PORT, rememberTransport: false});
socket.connect();

socket.on('connect', function() {
   $('form#respond').submit(function() {
      var answer = $.trim($('#answer').val());
      if (!answer.length || question_handler.has_sent_answer()) {
	 return false;
      }
      question_handler.send_answer(answer);
      return false;
   });
   $('#load-alternatives').click(function() {
      $('#answer').attr('readonly','readonly').attr('disabled','disabled');
      alternatives.load();
   });
});

socket.on('message', function(obj){
   __log_message(obj);
   if (obj.question) {
      question_handler.load_question(obj.question);
   } else if (obj.wait && obj.message) {
      setTimeout(function() {
         socket.send(obj.message);
      }, obj.wait * 1000);
   } else if (obj.winner) {
      if (obj.winner.draw) {
	 question_handler.finish(null, true);
      } else {
	 question_handler.finish(obj.winner.you_won);
      }
   } else if (obj.update_scoreboard) {
      if (-1 == obj.update_scoreboard[1]) {
	 scoreboard.drop_score(obj.update_scoreboard[0]);
      } else {
	 scoreboard.incr_score(obj.update_scoreboard[0], obj.update_scoreboard[1]);
      }
   } else if (obj.alternatives) {
      alternatives.show(obj.alternatives);
   } else if (obj.init_scoreboard) {
      $('#scoreboard:hidden').show(500);
      scoreboard.init_players(obj.init_scoreboard);
   } else if (obj.stop) {
      question_handler.stop(obj.stop);
   } else if (obj.answered) {
      $('#timer').hide();
      $('#input').hide();
      if (obj.answered.right) {
	 Clock.stop();
	 question_handler.right_answer();
      } else if (obj.answered.too_slow) {
	 question_handler.too_slow();
      } else {
	 Clock.stop();
	 question_handler.wrong_answer();
      }
   } else if (obj.error) {
      question_handler.stop();
      alert("Error!\n" + obj.error);
   } else if (obj.your_name) {
      // this is mainly for checking that all is working fine
      $('#your_name strong').text(obj.your_name);
      $('#your_name:hidden').show(500);
   }
});
