var chart;
head.ready(function() {

   chart = new Highcharts.Chart({
      chart: {
         renderTo: 'container',
         defaultSeriesType: 'bar'
      },
      title: {
         text: DATA.title
      },
      xAxis: {
         categories: DATA.x_categories
      },
      yAxis: {
         allowDecimals: false, // affects the xAxis because it's stacked
         min: 0,
         title: {
            text: DATA.y_title
         }
      },
      legend: {
         backgroundColor: Highcharts.theme.legendBackgroundColorSolid || '#FFFFFF',
         reversed: true
      },
      tooltip: {
         formatter: function() {
            return ''+
                this.series.name +': '+ this.y +'';
         }
      },
      plotOptions: {
         series: {
            stacking: 'normal'
         }
      },
      series: DATA.series
   });


});
