var MoreInfo = (function() {
  return {
     load: function (what, timestamp) {
       $.getJSON('/stats/no-questions-point.json',
                 {timestamp: timestamp, what: what},
                 function (response) {
                   $('#more-info ul li').remove();
                   var li, a;
                   $.each(response.items, function(i, item) {
                     li = $('<li>')
                     if (item.url) {
                       a = $('<a>', {href: item.url})
                         .text(item.text)
                           .appendTo(li);
                     } else {
                       li.text(item.text);
                     }
                     li.appendTo($('#more-info ul'));
                   });
                   $('#more-info').show();
                   $('#more-info a.closer').click(function() {
                     $('#more-info').fadeOut(500);
                     return false;
                   });
                 });
     }
  }
})();

var chart;
head.js(JS_URLS.highcharts, function() {
   // define the options
   var options = {
      chart: {
         renderTo: 'graph-container',
          type: 'spline'
      },
      title: {
         text: 'Cumulative count of published questions and contributors'
      },
      subtitle: {
         text: ''
      },
      xAxis: {
         type: 'datetime',
         tickInterval: 7 * 24 * 3600 * 1000, // one week
         //tickInterval: 24 * 3600 * 1000, // one day
         tickWidth: 0,
         gridLineWidth: 1,
         labels: {
            align: 'left',
            x: 3,
            y: -3
         }
      },

      yAxis: [{ // left y axis
         title: {
            text: null
         },
         labels: {
            align: 'left',
            x: 3,
            y: 16,
            formatter: function() {
               return Highcharts.numberFormat(this.value, 0);
            }
         },
         showFirstLabel: false
      }, { // right y axis
         linkedTo: 0,
         gridLineWidth: 0,
         opposite: true,
         title: {
            text: null
         },
         labels: {
            align: 'right',
            x: -3,
            y: 16,
            formatter: function() {
               return Highcharts.numberFormat(this.value, 0);
            }
         },
         showFirstLabel: false
      }],

      legend: {
         align: 'left',
         verticalAlign: 'top',
         y: 20,
         floating: true,
         borderWidth: 0
      },

      tooltip: {
         shared: true,
         crosshairs: true
      },

      plotOptions: {
         series: {
            cursor: 'pointer',
            point: {
               events: {
                  click: function() {
                    MoreInfo.load(this.series.name, this.x);
                  }
               }
            },
            marker: {
               lineWidth: 0
            }
         }
      },

      series: [{
         name: 'Contributors'
      }, {
         name: 'Questions'
      }
     ]
   };


  $.getJSON('/stats/no-questions.json', {cumulative: true}, function(response) {
    var contributors = [], questions = [];
    $.each(response.contributors, function(i, item) {
      contributors.push([item.t * 1000, item.c]);
    });
    $.each(response.questions, function(i, item) {
      questions.push([item.t * 1000, item.c]);
    });
    options.series[0].data = contributors;
    options.series[1].data = questions;
    chart = new Highcharts.Chart(options);
  });


});
