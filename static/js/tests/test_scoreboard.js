$(function() {
   scoreboard.init_players(['peter','ashley']);
   setTimeout(function() {
      scoreboard.incr_score('peter', 3);
      setTimeout(function() {
         scoreboard.incr_score('ashley', 1);
         setTimeout(function() {
            scoreboard.incr_score('peter', 3);
         }, 3*1000);
      }, 3*1000);
   }, 2*1000);
});
