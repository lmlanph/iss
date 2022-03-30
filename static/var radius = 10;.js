// var radius = 10;
// var svg = d3.select('svg');  
// var dimension = document.body.getBoundingClientRect();

// var data = d3.range(0, 25).map(function() {
//     return {
//     x: getRandom(radius, dimension.width - radius),
//     y: getRandom(radius, dimension.height - radius)
//   }
// });

var zoom = d3.zoom()
    .on('zoom', function() {
    canvas.attr('transform', d3.event.transform);
  })

var canvas = svg
    .attr('width', dimension.width)
  .attr('height', dimension.height)
  .call(zoom)
  .insert('g', ':first-child');

  
canvas.selectAll('circle')



  .data(data)
  .enter()
  .append('circle')
  .attr('r', radius)
  .attr('cx', function(d) {
    return d.x;
  }).attr('cy', function(d) {
    return d.y;
  }).style('fill', function() {
    return d3.schemeCategory10[getRandom(0, 9)]
  });









d3.select('#zoom-in').on('click', function() {
  // Smooth zooming
    zoom.scaleBy(svg.transition().duration(750), 1.3);
});

d3.select('#zoom-out').on('click', function() {
  // Ordinal zooming
  zoom.scaleBy(svg, 1 / 1.3);
});


// function getRandom(min, max) {
//   min = Math.ceil(min);
//   max = Math.floor(max);
//   return Math.floor(Math.random() * (max - min + 1)) + min;
// }