var PlayableQuestions = (function() {
  function refresh() {
    var data = {
       genres: [],
      pictures_only: $('#pictures_only:checked').size() ? 'yes' : ''
    };
    $('#id_genres option:selected').each(function(i, e) {
      data.genres.push($(e).val());
    });
    $.getJSON('/rules/playable_questions.json', data, function(response) {
      if (!$('#playables_hint').size()) {
        $('<div>', {id: 'playables_hint'})
          .append($('<h3>', {html: 'Number of playable questions: <span></span>'}))
            .insertBefore($('#id_genres'));
      }
      $('#playables_hint span').text(response.questions);
    });
  }
  return {
     init: function() {
       // pretend there was a change to genres
       refresh();
       $('#id_genres, #pictures_only').change(refresh);
     }
  }
})();

head.ready(function() {
  $('input[type="number"]').bind('keyup', function() {
    $(this).val($(this).val().replace(/[^\d]+/, ''));
  });

  PlayableQuestions.init();
});
