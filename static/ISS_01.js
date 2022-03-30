/*
note
*/

var w = 1400;
var h = 500;

var zoom = d3.zoom()
    .on('zoom', function() {
    canvas.attr('transform', d3.event.transform);
  })

var svg = d3.select("svg")
    .attr("preserveAspectRatio", "xMinYMin meet")
    .attr("viewBox", "0 0 " + w + " " + h);




// for remote/production
// note that since obtaining the domain spacewa.com am going to simple 'relative' path
// previously had used (elastic) ip address of the server here
// let route = "/data"

// for local dev
// should this be 8000 for gunicorn? was set to 5000
let route = "http://127.0.0.1:5000/data" 


let points = d3.json(route);

var map = d3.json("../static/N_AM.json");
var cities = d3.csv("../static/cities_long_lat.csv");

console.log(points)

var canvas = svg
    .call(zoom)
    .insert('g', ':first-child');

Promise.all([map, points, cities]).then(function(mapData) {
    
    // console.log(mapData[2]);
    
    var myMap = topojson.feature(mapData[0], {
        type:"GeometryCollection",
        geometries: mapData[0].objects.Political_Boundaries_Area.geometries
    });

    let projection = d3.geoMercator()
        .translate([w/2, h/2])
        .scale(590)
        // .scale(100)
        .center([-140,47]);

    var path = d3.geoPath()
        .projection(projection);

    canvas.selectAll("path")
        .data(topojson.feature(mapData[0], mapData[0].objects.Political_Boundaries_Area).features)
        .enter()
        .append("path")
        .attr("d", path)

    //ISS location
    canvas.selectAll("circle")
        .data(mapData[1])
        .enter()
        .append("circle")
        .attr("class","circles")
        .attr("cx", function(d) {
            return projection([d[1], d[0]])[0]; //these are mixed up, API data arrays/indexes need clarification
        })
        .attr("cy", function(d) {
            return projection([d[1], d[0]])[1];
        })
        .attr("r", "1px")
        .transition()
        .delay(function(d,i){ //set delay by element index
            return i * 25;
        })
        .duration(1000)
        .ease(d3.easeQuad)
        .attr("r", "25px")

        .transition()
        .duration(50000)
        .delay(function(d,i){
            return i * 2000;
        })
        .ease(d3.easeLinear)
        .style("opacity", 0);

    // cities location
    canvas.selectAll("ellipse")
        .data(mapData[2])
        .enter()
        .append("ellipse")
        .attr("class","cities")
        .attr("cx", function(d) {
            return projection([d.long, d.lat])[0];
        })
        .attr("cy", function(d) {
            return projection([d.long, d.lat])[1];
        })
        .attr("rx", "2px")
        .attr("ry", "2px")


    // called from setInterval...
    function updateData() {

        let points2 = d3.json(route);
        // console.log(points2)
        Promise.all([points2]).then(function(mapData) {
            
            // ISS location updated?
            let myCirc = canvas.selectAll("circle")
                .data(mapData[0])
                
            myCirc
                .exit()
                // .remove()
                    
            myCirc
                .enter().append("circle")
                .attr("class","circles")
                .attr("cx", function(d) {
                    return projection([d[1], d[0]])[0]; //these are mixed up, API data arrays/indexes need clarification
                })
                .attr("cy", function(d) {
                    return projection([d[1], d[0]])[1];
                })
                .attr("r", "1px")

                // .transition()
                // .duration(1000)
                // .attr("opacity", "0")
                
                .transition()
                .duration(1000)
                .ease(d3.easeQuad)
                .attr("r", "25px")

            myCirc
                .transition()
                .duration(10000)
                .ease(d3.easeQuad)
                .attr("opacity", "0")


            });

    }

    // update data every n miliseconds...
    var inter = setInterval(function() {
                updateData();
                // alert('well hey there!');
            }, 5000);

    // zoom in zoom out controls
    d3.select('#zoom-in').on('click', function() {
        zoom.scaleBy(svg.transition().duration(750), 2.5);
    });
    d3.select('#zoom-out').on('click', function() {
      zoom.scaleBy(svg.transition().duration(750), 1 / 2.5);
    });

        
});


