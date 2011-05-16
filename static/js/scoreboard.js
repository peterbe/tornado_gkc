var scoreboard = (function() {
   var _player_names
     , _ids = {}
     , _scores = {};

   function _init_table() {
      return $('<table>');
   }

   function _init_row(name) {
      var container = $('<tr>')
      var name = $('<td>', {text: name})
        .addClass('player_name')
          .appendTo(container);
      var score = $('<td>')
        .addClass('score')
          .text('0')
            .appendTo(container);
      return container;
   }

   function _display(id, name, score) {
      $('#scoreboard').html('');
      var name, score, increment, player_name
        , container, table = $('<table>');
      for (var i in _player_names) {
         container = $('<tr>');
         player_name = _player_names[i];
	 score = _scores[player_name];
	 name = $('<td>', {text: player_name})
           .addClass('player_name')
             .appendTo(container);
         if (increment || score >= 0) {
            var cell = $('<td>')
              .addClass(increment == player_name ? 'increment': 'score')
                .text(score)
                  .appendTo(container);
	 } else {
            var cell = $('<td>')
              .addClass('disconnected')
                .text("Disconnected")
                  .appendTo(container);
	    name.addClass('disconnected');
	 }
         table.append(container);
      }
      $('#scoreboard').append(table);
      if (typeof(callback) !== 'undefined') {
         setTimeout(function() {
            $('#scoreboard td.increment').fadeOut(600, function() {
               L('faded out');
               callback();
            });
         }, 1000);
      }
   }
   return {
      init_players: function(player_names) {
         var table = _init_table();
         var id, row;
	 for (var i in player_names) {
            id = 'sp_' + i;
            row = _init_row(player_names[i]);
            row.attr('id', id).appendTo(table);
            _ids[player_names[i]] = id;
            _scores[player_names[i]] = 0;
	 }
         table.appendTo($('#scoreboard'));
      },
      drop_score: function(player_name) {
	 _scores[player_name] = -1;
	 _display(player_name);
      },
      incr_score: function(player_name, points) {
         var row = $('#' + _ids[player_name]);
         _scores[player_name] += points;
         var score = _scores[player_name];
         $('td.score', row)
           .text('+' + points)
             .addClass('increment')
               .removeClass('score');
         setTimeout(function() {
            $('td.increment').fadeTo(500, 0.1, function() {
               $(this)
                 .removeClass('increment')
                   .addClass('score')
                     .text(score)
                       .fadeTo(400, 1.0);
            });
         }, 1000);
      }
   }
})();
