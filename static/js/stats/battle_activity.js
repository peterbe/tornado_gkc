var chart;
head.js(JS_URLS.highcharts, function() {
   // define the options
   var options = {
      chart: {
         renderTo: 'graph-container',
          type: 'spline'
      },
      title: {
         text: 'Battle activity'
      },
      subtitle: {
         text: 'Only counting finished battles'
      },
      xAxis: {
         type: 'datetime',
         //tickInterval: 7 * 24 * 3600 * 1000, // one week
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
            },
            marker: {
               lineWidth: 0
            }
         }
      },

      series: [{
         name: 'Against the Computer'
      }, {
         name: 'Multiplayer battles'
      }
     ]
   };


  jQuery.get('/stats/battle-activity.json', null, function(response) {
    var solos = [], multis = [];

    $.each(response.solos, function(i, item) {
      solos.push([item.t * 1000, item.c]);
    });
    $.each(response.multis, function(i, item) {
      multis.push([item.t * 1000, item.c]);
    });
    options.series[0].data = solos;
    options.series[1].data = multis;
    chart = new Highcharts.Chart(options);
  });

});
