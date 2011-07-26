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
}

function esc(msg) {
   return msg.replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

var Title = (function() {
   var current_title = document.title
     , timer;

   return {
      show_temporarily: function (msg, msec) {
         msec = typeof(msec) !== 'undefined' ? msec : 3000;
	 if (msec < 100) msec *= 1000;
         if (timer) {
            clearTimeout(timer);
         }
         document.title = msg;
         timer = setTimeout(function() {
            document.title = current_title;
         }, msec);
      }
   }
})();


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
        if (p < 40) {
          rumbleSpeed = 1 * p;
          var range;
          if (p < 1) range = 8;
          else if (p < 3) range = 6;
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
    , _timer_bot
    , _has_answered = false;

  return {
     is_initialized: function() {
       return _initialized;
     },
    initialize: function() {
      $('#respond').show();
      $('#waiting').hide();
      $('#your_name').hide();
      $('#play_right').remove();

      _initialized = true;
    },
    load_question: function(question) {
      if (!_initialized) {
        this.initialize();
      }
      if (_timer_bot) clearTimeout(_timer_bot);
      _has_answered = false;
      _current_question = question;
      $('#timer:hidden').show();
      $('#input:hidden').show();
      $('#alternatives input.alternative').remove();
      $('#alternatives-outer:visible').hide();
      $('#load-alternatives:hidden').show();
      $('#typed:hidden').show();
      $('#answer').removeAttr('readonly').removeAttr('disabled').val('');
      $('#question li.current').removeClass('current').addClass('past');
      $('#images img').remove();
      var question_text = question.text;
      if (question.image) {
        question_text = '(image question) ' + question_text;
      }
      $('#question').append($('<li>', {id: question.id}
                             ).addClass('current')
                            .append($('<span>', {text: question_text})));
      $('#alternatives').fadeTo(0, 1.0);
      $('#alert').hide();
      $('#gossip').hide();
      Clock.stop();

      if (question.image) {
        // don't start the timer
        $('li.current').hide();
        var image = $('<img>')
          .attr('width', question.image.width)
            .attr('height', question.image.height)
              .attr('alt', question.image.alt)
                .ready(function() {
                  send({loaded_image: 1});
                }).appendTo($('#images'));
        image.attr('src', question.image.src);
      } else {
        Clock.start(this.timed_out);
        $('#answer').focus();
      }
      // check if an image was loaded to the previous question
      if (!$('img', $('li.past').eq(-1)).size()) {
        $('li.past').eq(-1)
          .append($('<img>', {
             src: IMAGES.HOURGLASS,
              alt: 'Timed out'
          }));
      }
    },
    show_image: function() {
      $('li.current').show();
      Clock.start(this.timed_out);
      $('#answer').focus();
    },
    bot_answers: function(seconds) {
      _timer_bot = setTimeout(function() {
        send({bot_answers: true});
      }, seconds * 1000);
    },
    clear_bot_answers: function() {
      clearTimeout(_timer_bot);
    },
    timed_out: function() {
      if (_timer_bot) clearTimeout(_timer_bot);
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
      if (_timer_bot) clearTimeout(_timer_bot);
      $('#alert').hide();
      $('#gossip').hide();
      $('#input').hide();
      Question.stop();
      draw = draw || false;
      $('#question li.current').removeClass('current').addClass('past');
      if (draw) {
        Title.show_temporarily("You drew!", 30);
        $('#you_drew').fadeIn(300);
      } else {
        if (you_won) {
          if (CONFIG.ENABLE_SOUNDS && soundManager && CONFIG.SOUNDS) {
            soundManager.play(CONFIG.SOUNDS['you_won']);
          }
          Title.show_temporarily("You won!! Congratulations!", 30);
          $('#you_won').fadeIn(300);
        } else {
          if (CONFIG.ENABLE_SOUNDS && soundManager && CONFIG.SOUNDS) {
            soundManager.play(CONFIG.SOUNDS['you_lost']);
          }
          Title.show_temporarily("You lost. Sorry(?)", 30);
          $('#you_lost').fadeIn(300);
        }
      }
      setTimeout(function() {
        $('#questions_ad:hidden').show(700);
      }, 5 * 1000);
    },
    stop: function(information) { // the whole battle is over
      Clock.stop();
      $('#timer').hide();
      $('#input').hide();
      $('#images img').remove();
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
      Title.show_temporarily(msg);
      $('#alert').text(msg).show();
    },
    wrong_answer: function() {
      var msg = 'Sorry. You got it wrong';
      $('li.current')
        .append($('<img>', {
           src: IMAGES.WRONG,
            alt: msg
        }));
      Title.show_temporarily(msg);
      $('#alert').text(msg).show();
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
      Title.show_temporarily(msg);
      $('#alert').text(msg).show();
    },
    beaten: function() {
      var msg = 'Sorry. Opponent beat you on that question';
      /*$('li.current')
       .append($('<img>', {
       src: IMAGES.WRONG,
       alt: msg
       }));*/
      Title.show_temporarily(msg);
      $('#alert').text(msg).show();
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
  if (!$('#log:visible').size()) return;
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
var socket
, dead_battle = false
, confirm_exit = true
, has_connected = false
, still_alive_interval
;

$(function() {
  socket = new io.Socket(null, {port: CONFIG.SOCKET_PORT, rememberTransport: false});


  var waiting_message_interval = setInterval(function() {
    var text = $('#waiting .message').text();
    if (text.length > 50) {
      text = text.replace(/\.{3,50}/, '...');
    }
    $('#waiting .message').text(text + '.');
  }, 1000);

  socket.on('connect', function() {
      /*
       * Commented out because it breaks things horribly.
       * It would be better if re-connection just worked without
       * creating a new battle.
      if (has_connected) {
         // don't allow it to re-connect if
         $('#error_warning').show();
         $('#error_warning pre').text("Re-connected");
         dead_battle = true;
         $(window).unbind('beforeunload');
         return;
      } else {
         has_connected = true;
      }
       */

     clearInterval(waiting_message_interval);
     $('#waiting .message').text('Waiting for an opponent');
     waiting_message_interval = setInterval(function() {
       var text = $('#waiting .message').text();
       if (text.length > 100) {
         text = text.replace(/\.{3,100}/, '...');
       }
       $('#waiting .message').text(text + '.');
     }, 1000);

     $('#challenge-computer a.more-info').click(function() {
       if ($('#challenge-computer p.more-info:visible').size()) {
         $(this).text('More info');
         $('#challenge-computer p.more-info').hide();
       } else {
         $(this).text('Hide info');
         $('#challenge-computer p.more-info').show();
       }
       return false;
     });

     $('#challenge-computer').submit(function() {
       if (!first_wait) return false;
       send({against_computer:1});
       return false;
     }).show(700);

     setTimeout(function() {
       if (!$('.error:visible').size() && !Question.is_initialized()) {
         $('#besocial').show(700);
       }
     }, 5 * 1000);

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

     var delay = 3;
     still_alive_interval = setInterval(function() {
       send({still_alive: true});
       delay += 0.1;
     }, Math.ceil(delay * 1000));
   });


  var first_wait = true;
  socket.on('message', function(obj) {
    if (dead_battle) return;
    __log_message(obj, false);
    if (obj.question) {
      clearInterval(waiting_message_interval);
      clearInterval(still_alive_interval);
      Question.load_question(obj.question);
    } else if (obj.show_image) {
      Question.show_image();
    } else if (obj.wait && obj.message) {
      if (first_wait) {
        $('#your_name').hide();
        $('#challenge-computer').hide();
        $('#waiting').hide();
        $('#play_right').remove();

        if (CONFIG.ENABLE_SOUNDS && soundManager && CONFIG.SOUNDS) {
          soundManager.play(CONFIG.SOUNDS['be_ready']);
        }
        Title.show_temporarily("Ready!? Game about to start!!");
      }
      Question.clear_bot_answers();
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
      Question.clear_bot_answers();
      Question.stop(obj.stop);
    } else if (obj.has_answered) {
      var msg = obj.has_answered + ' has answered but was wrong';
      Title.show_temporarily(msg, 3 * 1000);
      Gossip.show(msg);
    } else if (obj.answered) {
      $('#timer').hide();
      $('#input').hide();
      Clock.stop();
      if (obj.answered.right) {
        //Clock.stop();
        Question.right_answer();
      } else if (obj.answered.too_slow) {
        Question.too_slow();
      } else if (obj.answered.beaten) {
        Question.beaten();
      } else {
        //Clock.stop();
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
      $('#play_right').hide();
      $('#your_name').hide();
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
      $('#your_name:hidden').show(400);
    }

    // things that might be included with any other message
    if (obj.thinking_time) {
      Clock.set_thinking_time(obj.thinking_time);
    }
    if (obj.bot_answers) {
      Question.bot_answers(obj.bot_answers);
    }
    if (obj.init_scoreboard) {
      scoreboard.init_players(obj.init_scoreboard);
      $('#scoreboard:hidden').show(500);
    }
    if (obj.play_id) {
      $('a.replay').attr('href', '/play/replay/' + obj.play_id  + '/');
      $.getJSON('/play/update_points.json', {play_id: obj.play_id}, function(response) {
        if (response.anonymous) {
          $('<span>')
            .text("You just earned yourself " + response.points + " Kwissle points!")
              .appendTo($('.points'));
          $('<br>')
            .appendTo($('.points'));
          $('<a>')
            .attr('href', response.login_url)
              .attr('title', 'Click to register your high score')
                .text('Click here to register and save your highscore')
                  .appendTo($('.points'));
        } else if (response.increment) {
          $('<a>')
            .attr('href', '/play/highscore/')
              .attr('title', 'Click to see where you are in the Highscore list')
                .text("You just earned yourself " + response.increment + " more Kwissle points!")
                  .appendTo($('.points'));
          $('<br>')
            .appendTo($('.points'));
          $('<span>')
            .html("You're now number <span class=\"yellow\">" +response.highscore_position + " in the Highscore list</span>")
              .appendTo($('.points'));
        }
      });
    }
  });
  socket.on('disconnect', function() {
    clearInterval(waiting_message_interval);
    clearInterval(still_alive_interval);
  });

  socket.connect();

  $('a').click(function() {
    confirm_exit = false;
    $(window).unbind('beforeunload');
  });

  $(window).bind('beforeunload', function() {
    return "Sure you want to exit? Hit Escape to stay.";
  });

  // Annoyingly this only works the first time with Chrome
  shortcut.add('backspace', function() {
    // void
  }, {disable_in_input:true});

});
