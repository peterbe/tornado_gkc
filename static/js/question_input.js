/* Nothing yet */


var Form = (function() {
   function shuffle(o) { //v1.0
      for (var j, x, i = o.length; i;
	   j = parseInt(Math.random() * i), x = o[--i], o[i] = o[j], o[j] = x);
      return o;
   };

   return {
      has_all_alternatives: function() {
         var count = 0;
         $('input[name="alternatives"]').each(function(i,e) {
            if ($(this).val().length) {
               count++;
            }
         });
         return count >= 4;
      },
      shuffle_alternatives: function(animate) {
         animate = animate != null ? animate : 15;
         var alts = [];
         $('input[name="alternatives"]').each(function(i,e) {
            alts.push($(this).val());
         });
         alts = shuffle(alts);
         $('input[name="alternatives"]').each(function(i,e) {
            $(this).val(alts[i]);
         });
         if (animate > 0) {
            setTimeout(function() {
               Form.shuffle_alternatives(animate - 1);
            }, 40 + (10 * (20 - animate)));
         }
      },
      add_shuffler: function() {
         $('<a>', {href: '#', text: 'shuffle!'})
           .addClass('shuffler')
	     .addClass('bold')
             .click(function() {
                if (Form.has_all_alternatives) {
                   Form.shuffle_alternatives();
                }
		$('a.bold').removeClass('bold');
                return false;
             })
               .insertAfter($('input[name="alternatives"]').eq(-1));
      }
   };
})();

var GENRE_NAMES;
head.js(JS_URLS.jquery_autocomplete, function() {
   $.getJSON('/questions/genre_names.json', {separate_popular: true}, function(r) {
      var preval = $('#genre').val(), preval_element;
      $('#genre').hide();
      var container, big_container = $('#genre').parents('p.field');

      $.each(r.popular_names, function(i, e) {
	 container = $('<span>').addClass('genre-field');
         $('<input type="radio" name="chosen_genre">')
           .attr('id', 'g_' + i)
             .val(e[1])
               .change(function() {
                  $('#id_other_genre').fadeTo(300, 0.2);
               })
           .appendTo(container);
         if (e[1] == preval) {
            preval_element = $('#g_' + i);
         }
         $('<label>',
           {title: e[0] + ' questions',
            text: e[1],
            'for': 'g_' + i})
           .addClass('genre')
           .appendTo(container);
	 if (i && 0 == i % 6) {
	   $('<br>').appendTo(container);
	 }

	 big_container.append(container);
      });

      $('<br>').appendTo(big_container);
      $('<input type="radio" name="chosen_genre">')
        .attr('id', 'g_other')
          .val('other')
            .change(function() {
               $('#id_other_genre').fadeTo(300, 1);
            })
          .appendTo(big_container);
      $('<label>', {text: 'Other:', 'for': 'g_other'})
        .addClass('genre')
        .appendTo(big_container);
      $('<input type="text" name="other_genre" id="id_other_genre">')
        .autocomplete(r.all_names)
          .bind('focus', function() {
             $('input[value="other"]').attr('checked', 'checked');
             $('#id_other_genre').fadeTo(300, 1);
          })
        .appendTo(big_container);

      if (preval_element) {
         preval_element.attr('checked', 'checked');
      } else if (preval) {
         $('#id_other_genre').val(preval);
         $('#g_other').attr('checked', 'checked');
      }
      //$('input[name="genre"]').autocomplete(r.names);


   });
});

head.js(JS_URLS.jquery_tipsy, function() {
   $('textarea').tipsy({trigger: 'focus', gravity: 'se', fade: true});
   $('input[title]')
     .not('#spell_correct,#genre')
       .not('input[type="submit"]')
       .tipsy({trigger: 'focus', gravity: 'ne', fade: true});
   $('#spell_correct').tipsy({trigger: 'hover', gravity: 'w', fade: true});
   $('#genre').tipsy({trigger: 'hover', gravity: 'sw', fade: true});
   $('input[type="submit"]').tipsy({trigger: 'hover', gravity: 'w', fade: true});
});

head.js(JS_URLS.maxlength_countdown, function() {
   $('input[maxlength]').maxlength_countdown();
});

head.ready(function() {
   var uniqify = function(seq, case_insensitive) {
      var copy = [];
      case_insensitive = case_insensitive === undefined ? false : true;
      var item;
      for (var i = 0, j = seq.length; i < j; i++) {
         item = seq[i];
         if (case_insensitive && typeof(item) == 'string')
           item = item.toLowerCase();
         if (-1 == copy.indexOf(item)) {
            copy.push(item);
         }
      }
      return copy;
   };
   if (Form.has_all_alternatives()) {
      Form.add_shuffler();
   }
   $('form[method="post"]', '#content_inner').submit(function() {
      var text = $('input[name="text"]').val();
      if (!$.trim(text)) {
         alert('Please enter the question');
         return false;
      }
      var answer = $('input[name="answer"]').val();
      if (!$.trim(answer)) {
         alert('Please enter the answer');
         return false;
      }
      var alternatives = [];
      $('input[name="alternatives"]').each(function() {
         if ($(this).val().length) {
            alternatives.push($(this).val());
         }
      });
      if (alternatives.length >= 4) {
         if (-1 == alternatives.indexOf(answer)) {
            alert('One of the alternatives must be the answer');
            return false;
         }

      } else {
         alert('Please fill in 4 alternatives');
         return false;
      }
      if (uniqify(alternatives, true).length < 4) {
         alert('Please enter 4 *different* alternatives');
         return false;
      }

      var chosen_genre = $('input[name="chosen_genre"]:checked').val();
      if (chosen_genre == 'other')
        chosen_genre = $('input[name="other_genre"]').val();
      $('input[name="genre"]').val(chosen_genre);
      return true;
   });
   $('input[name="alternatives"]').change(function() {
      if ($(this).val().length && Form.has_all_alternatives() && !$('.shuffler').size()) {
         Form.add_shuffler();
      }
   });
   $('input[name="answer"]').change(function() {
      if ($(this).val().length && ! Form.has_all_alternatives()) {
         var _added = false;
         $('input[name="alternatives"]').each(function(i, e) {
            if (!_added && !$(this).val().length) {
               $(this).val($('input[name="answer"]').val());
               _added = true;
            }
         });
      }
   });




   // on the Edit question page
   //$('input[name="submit_question"]').click(function() {
   //   return confirm("Are you sure?\nQuestion can not be edited after this.");
   //});
});
