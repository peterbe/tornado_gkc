var highchartsOptions;
function _create_chart_theme() {
  function shuffle(o) { //v1.0
    for (var j, x, i = o.length; i;
         j = parseInt(Math.random() * i), x = o[--i], o[i] = o[j], o[j] = x);
    return o;
  };
  var COLORS = ["#DDDF0D", "#7798BF", "#55BF3B", "#DF5353", "#aaeeee", "#ff0066", "#eeaaee",
                "#55BF3B", "#DF5353", "#7798BF", "#aaeeee"];
  COLORS = shuffle(COLORS);
  //console.log(COLORS[0]);
  //console.log(COLORS[1]);
  Highcharts.theme = {
     colors: COLORS,
    title: {
       style: {
          color: '#FFF',
       }
    },
    xAxis: {
       gridLineWidth: 0,
        lineColor: '#999',
        tickColor: null,
        labels: {
           style: {
              color: '#ccc',
               fontWeight: 'bold'
           }
        },
      title: {
         style: {
            color: '#ccc',
             font: 'bold 12px Lucida Grande, Lucida Sans Unicode, Verdana, Arial, Helvetica, sans-serif'
         }
      }
    },

    legend: {
       itemStyle: {
          color: '#efefef'
       }
    },


  };
  highchartsOptions = Highcharts.setOptions(Highcharts.theme);

}



function _create_chart(categories, series) {
  chart = new Highcharts.Chart({
     chart: {
        renderTo: 'scoreboard-graph',
         defaultSeriesType: 'line',
         backgroundColor: null,
         height: 370, width: 700

      },
     credits: { enabled:false },
      title: {
         text: ''
      },
     legend: {
        borderColor: null,
         align: 'center',
        verticalAlign: 'top',
        x: 20,
        y: 15,
        floating: true
     },
      xAxis: {
         title: {
            text: 'Questions'
         },
         categories: categories,
          endOnTick: false, max: categories.length - 1
      },
      yAxis: {
         gridLineWidth:0,
          labels: { enabled: false },
         title: {
            text: ''
         },
        min: 0
      },
      tooltip: {
         enabled: false,
         formatter: function() {
            return '<b>'+ this.series.name +'</b><br/>'+
               this.x +': '+ this.y;
         }
      },
      plotOptions: {
         series: {
            marker: {
               radius: 4
            }
         },
         line: {
            lineWidth: 3,
            dataLabels: {
               enabled: true
            },
            enableMouseTracking: false
         }
      },
     series: series
   });

}

var chart;

head.js(JS_URLS.maxlength_countdown, JS_URLS.highcharts, JS_URLS.fancybox, function() {
  $("a.thumbnail").fancybox();
  if (location.hash.search(/message_sent/) > -1) {
    $('#message_sent').show();
  } else {
    $('input[maxlength]').maxlength_countdown();
    $('#send_message').show(900);
  }

  _create_chart_theme();
  var categories = [];
  for (var i=0, len=SERIES[0].data.length; i < len; i++) {
    if (i == 0) {
      categories.push('start');
    } else {
      categories.push('' + (i));
    }
  }
  _create_chart(categories, SERIES);

});
