var L = function() {
   if (window.console && window.console.log)
     console.log.apply(console, arguments);
};

function message(obj) {
   var el = document.createElement('p');
   if ('announcement' in obj) el.innerHTML = '<em>' + esc(obj.announcement) + '</em>';
   else if ('message' in obj) el.innerHTML = '<b>' + esc(obj.message[0]) + ':</b> ' + esc(obj.message[1]);
   document.getElementById('chat').appendChild(el);
   document.getElementById('chat').scrollTop = 1000000;
}

function send(msg) {
   __log_message(msg, true);
   socket.send(msg);
   //var val = document.getElementById('text').value;
   //socket.send(val);
   //message({ message: ['you', val] });
   //document.getElementById('text').value = '';
}

function esc(msg) {
   return msg.replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

var Clock = (function() {
   var _clock
, _seconds_left
, _callback
, _init_seconds
, _thinking_time;
   return {
      stop: function() {
	 clearTimeout(_clock);
      },
      start: function(callback) {
         if (_thinking_time === null) throw 'Thinking time not set';
	 Rumbler.stop();
	 _init_seconds = _thinking_time;
	 Clock.tick(_thinking_time);
	 _callback = callback;
      },
      tick: function(seconds) {
         _seconds_left = seconds;
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
	       if (p < 1) range = 8;
	       else if (p < 5) range = 4;
	       else if (p < 10) range = 3;
	       else range = 2;
	       Rumbler.start($('#timer'), rumbleSpeed, range);
	    }
	 } else {
	    _callback();
	 }
      },
      get_thinking_time: function() {
         return _thinking_time;
      },
      set_thinking_time: function(t) {
         _thinking_time = t;
      },
      get_seconds_left: function() {
         return _seconds_left;
      }
   };
})();


var Question = (function() {
   var _current_question
, _initialized = false
, _timer_callback
, _has_answered = false;

   return {
      is_initialized: function() {
	 return _initialized;
      },
      initialize: function() {
	 $('#respond').show();
	 $('#waiting').hide();
	 $('#your_name').hide();
	 _initialized = true;
      },
      load_question: function(question) {
         //L("LOAD_QUESTION", question);
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
	 $('#alert').hide();
	 $('#gossip').hide();
	 Clock.stop();
	 Clock.start(this.timed_out);
	 $('#answer').focus();

	 // check if an image was loaded to the previous question
	 if (!$('img', $('li.past').eq(-1)).size()) {
	    $('li.past').eq(-1)
	      .append($('<img>', {
                 src: IMAGES.HOURGLASS,
		alt: 'Timed out'
	      }));
	 }
      },
      timed_out: function() {
	 $('#question li.current').addClass('past');
	 $('#answer').removeAttr('readonly');
	 var msg = 'Both too slow';
	 $('li.current')
	   .append($('<img>', {src: IMAGES.HOURGLASS,
		alt: msg
	   }));
	 $('#input').hide();
	 $('#timer').hide();
	 send({timed_out: true});
      },
      finish: function(you_won, draw) {
         $('#alert').hide();
         $('#gossip').hide();
	 $('#input').hide();
	 Question.stop();
	 draw = draw || false;
	 $('#question li.current').removeClass('current').addClass('past');
	 if (draw) {
            $('#you_drew').fadeIn(400);
	 } else {
	    if (you_won) {
               if (CONFIG.ENABLE_SOUNDS && soundManager) {
                  soundManager.play(CONFIG.SOUNDS['you_won']);
               }
               $('#you_won').fadeIn(400);
	    } else {
               if (CONFIG.ENABLE_SOUNDS && soundManager) {
                  soundManager.play(CONFIG.SOUNDS['you_lost']);
               }
               $('#you_lost').fadeIn(400);
	    }
	 }
	 setTimeout(function() {
	    $('#questions_ad:hidden').show(500);
	 }, 3 * 1000);
      },
      stop: function(information) { // the whole battle is over
	 Clock.stop();
	 $('#timer').hide();
	 $('#input').hide(500);
	 if (information && information.message) {
	    $('#information p').text(information.message);
	    $('#information').show();
	 }
      },
      right_answer: function() {
	 var msg = 'Yay! you got it right';
	 $('li.current')
	   .append($('<img>', {
              src: IMAGES.RIGHT,
		alt: msg
	   }));
	 $('#alert').text(msg).show(100);
      },
      wrong_answer: function() {
	 var msg = 'Sorry. You got it wrong';
	 $('li.current')
	   .append($('<img>', {
              src: IMAGES.WRONG,
		alt: msg
	   }));
	 $('#alert').text(msg).show(100);
         var left = Clock.get_seconds_left();
         if ((left - 1) > 0) {
            Gossip.count_down(left - 1, function (s) {
               return 'Opponent has ' + (s + 1) + ' seconds left. Be patient!';
            });
         }
      },
      too_slow: function() {
	 var msg = 'Sorry. You were too slow';
	 $('li.current')
	   .append($('<img>', {
              src: IMAGES.WRONG,
		alt: msg
	   }));
	 $('#alert').text(msg).show(100);
      },
      beaten: function() {
	 var msg = 'Sorry. Opponent beat you on that question';
	 /*$('li.current')
	   .append($('<img>', {
              src: IMAGES.WRONG,
		alt: msg
	   }));*/
	 $('#alert').text(msg).show(100);
      },
      send_answer: function(answer) {
         if (_has_answered) {
            alert('You have already answered this question');
         } else {
            Clock.stop();
            $('#answer').attr('readonly', 'readonly').attr('disabled', 'disabled');
            send({answer: answer});
            _has_answered = true;
         }
      },
      has_sent_answer: function() {
	 return _has_answered;
      }
   };
})();

var alternatives = (function() {
   return {
      load: function() {
	 $('#load-alternatives').hide();
	 send({alternatives: true});
      },
      show: function(alts) {
	 var container = $('#alternatives');
	 for (var i in alts) {
	    container.append($('<input>', {name: 'alternative', type: 'button', value: alts[i]})
			     .addClass('alternative')
			     .click(function() {
				alternatives.answer(this.value);
			     }));
	 }
	 $('#alternatives-outer').show();
	 $('#typed:visible').hide();
      },
      answer: function(ans) {
	 send({answer: ans});
	 $('#alternatives input.alternative')
	   .attr('readonly', 'readonly')
	     .attr('disable', 'disable')
	       .unbind('click');
	 $('#alternatives').fadeTo(300, 0.4);
      }
   };
})();

function __log_message(msg, inbound) {
   var el = $('<p>');
   var d = new Date();
   var line = '<em>';
   if (inbound) {
      line += '&larr;';
      el.addClass('inbound');
   } else {
      line += '&rarr;';
      el.addClass('outbound');
   }
   line += d.getHours() + ':' + d.getMinutes() + ':' + d.getSeconds() + '.' + d.getMilliseconds() + '</em> ';
   if ('object' == typeof msg) {
      line += JSON.stringify(msg);
   } else {
      line += msg;
   }
   el.html(line);

   //document.getElementById('log').appendChild(el);
   el.appendTo('#log');
   document.getElementById('log').scrollTop = 1000000;
}

var Gossip = (function() {
   var timer;
   return {
      show: function(msg, delay) {
         $('#gossip').text(msg).show();
         if (delay) {
            timer = setTimeout(function() {
               $('#gossip:visible').fadeOut(400);
            }, delay * 1000);
         }
      },
      clear: function() {
         $('#gossip').text('').hide();
      },
      count_down: function(seconds, message_maker) {
         if (seconds == 1) {
            Gossip.show(message_maker(seconds), 1);
         } else {
            Gossip.show(message_maker(seconds));
         }

         seconds--;
         if (seconds > 0) {
            setTimeout(function() {
               Gossip.count_down(seconds, message_maker);
            }, 1000);
         }
      }
   };
})();


// Let the madness begin!
var socket, dead_battle = false, confirm_exit = true;

$(function() {
   socket = new io.Socket(null, {port: CONFIG.SOCKET_PORT, rememberTransport: false});
   socket.connect();

   var waiting_message_interval = setInterval(function() {
      var text = $('#waiting .message').text();
      if (text.length > 50) {
         text = text.replace(/\.{3,50}/, '...');
      }
      $('#waiting .message').text(text + '.');
   }, 1000);

   socket.on('connect', function() {
      clearInterval(waiting_message_interval);
      $('#waiting .message').text('Waiting for an opponent');
      waiting_message_interval = setInterval(function() {
         var text = $('#waiting .message').text();
         if (text.length > 100) {
            text = text.replace(/\.{3,100}/, '...');
         }
         $('#waiting .message').text(text + '.');
      }, 1000);


      setTimeout(function() {
         if (!$('.error:visible').size() && !Question.is_initialized()) {
            $('#besocial').show(900);
         }
      }, 7 * 1000);

      $('form#respond').submit(function() {
         var answer = $.trim($('#answer').val());
         if (!answer.length || Question.has_sent_answer()) {
            return false;
         }
         Question.send_answer(answer);
         return false;
      });
      $('#load-alternatives').click(function() {
         $('#answer').attr('readonly', 'readonly').attr('disabled', 'disabled');
         alternatives.load();
      });
   });

   var first_wait = true;
   socket.on('message', function(obj) {
      if (dead_battle) return;
      __log_message(obj, false);
      if (obj.question) {
         clearInterval(waiting_message_interval);
         Question.load_question(obj.question);
      } else if (obj.wait && obj.message) {
         if (first_wait) {
            if (CONFIG.ENABLE_SOUNDS && soundManager) {
               soundManager.play(CONFIG.SOUNDS['be_ready']);
            }
            $('#besocial').remove();
         }
         var seconds_left = obj.wait;
         Gossip.count_down(obj.wait, function(seconds) {
            return 'Next question in ' + seconds + ' seconds';
         });
         setTimeout(function() {
            send(obj.message);
         }, obj.wait * 1000);
         first_wait = false;
      } else if (obj.winner) {
         if (obj.winner.draw) {
            Question.finish(null, true);
         } else {
            Question.finish(obj.winner.you_won);
         }
         dead_battle = true;
         $(window).unbind('beforeunload');
      } else if (obj.update_scoreboard) {
         if (-1 == obj.update_scoreboard[1]) {
            scoreboard.drop_score(obj.update_scoreboard[0]);
         } else {
            scoreboard.incr_score(obj.update_scoreboard[0], obj.update_scoreboard[1]);
         }
      } else if (obj.alternatives) {
         alternatives.show(obj.alternatives);
      } else if (obj.stop) {
         Question.stop(obj.stop);
      } else if (obj.has_answered) {
         Gossip.show(obj.has_answered + ' has answered but was wrong');
      } else if (obj.answered) {
         $('#timer').hide();
         $('#input').hide();
         if (obj.answered.right) {
            Clock.stop();
            Question.right_answer();
         } else if (obj.answered.too_slow) {
            Question.too_slow();
         } else if (obj.answered.beaten) {
            Question.beaten();
         } else {
            Clock.stop();
            Question.wrong_answer();
         }
      } else if (obj.disconnected) {
         scoreboard.drop_score(obj.disconnected);
         Question.stop();
         $('#error_disconnected').show();
	 $('#error_disconnected .user_name').text(obj.disconnected);
         dead_battle = true;
         $(window).unbind('beforeunload');
      } else if (obj.error) {
         Question.stop();
	 $('#waiting').hide();
	 $('#your_name').hide();
         //alert('Error!\n' + obj.error);
         $('#error_warning').show();
         $('#error_warning pre').text(obj.error.message);
         if (obj.error.code == 200) {
            $('#error_run_out').show();
         }
         dead_battle = true;
         $(window).unbind('beforeunload');
      } else if (obj.your_name) {
         // this is mainly for checking that all is working fine
         $('#your_name strong').text(obj.your_name);
         $('#your_name:hidden').show(500);
      }

      // things that might be included with any other message
      if (obj.thinking_time) {
         Clock.set_thinking_time(obj.thinking_time);
      }
      if (obj.init_scoreboard) {
         scoreboard.init_players(obj.init_scoreboard);
         $('#scoreboard:hidden').show(500);
      }
      if (obj.play_id) {
         $('a.replay').attr('href', '/play/replay/' + obj.play_id  + '/');
      }
   });

   $('a').click(function() {
      confirm_exit = false;
      $(window).unbind('beforeunload');
   });

   $(window).bind('beforeunload', function() {
      return "Sure you want to exit? Hit Escape to stay.";
   });


});
