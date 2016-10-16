
var getVegaSpec = function(table,DataViews,resourceIndex) {
  var price = DataViews[resourceIndex].state.series[0];
  var date = DataViews[resourceIndex].state.group;
  var parse = makeParse(date, price);
  var test = makeTest(date, "daily"); // needs to be automate (passed to datapackage.json or smth)
  var template = makeTemplate("daily");
  var spec = {
    "actions": false,
    "spec": {
      "width": 1080,
      "height": 500,
      "signals": [
        {
          "name": "mouseDate",
          "streams": [
            {
              "type": "mousemove",
              "expr": "eventX()",
              "scale": {"name": "x","invert": true}
            }
          ]
        },
        {
          "name": "mouseCount",
          "streams": [
            {
              "type": "mousemove",
              "expr": "eventY()",
              "scale": {"name": "y","invert": true}
            }
          ]
        }
      ],
      "data": [
        {
          "name": "data",
          "url": table.remoteurl,
          "format": {
            "type": "csv",
            "parse": parse
          }
        },
        {
          "name": "group",
          "source": "data",
          "transform": [
            {
              "type": "filter",
              "test": test
            }
          ]
        }
      ],
      "scales": [
        {
          "name": "x",
          "type": "time",
          "range": "width",
          "nice": "day",
          "domain": {"data": "data","field": date}
        },
        {
          "name": "y",
          "type": "linear",
          "range": "height",
          "nice": true,
          "zero": false,
          "domain": {"data": "data","field": price}
        }
      ],  
      "axes": [
        {"type": "x","scale": "x","ticks": 12,"grid": true},
        {"type": "y","scale": "y","ticks": 5,"grid": true}
      ],
      "marks": [
        {
          "name": "point",
          "type": "symbol",
          "from": {"data": "data"},
          "properties": {
            "enter": {
              "x": {"scale": "x","field": date},
              "y": {"scale": "y","field": price},
              "strokeWidth": {"value": 2}
            },
            "update": {
              "fill": {"value": "steelblue"},
              "size": {"value": "40"}
            },
            "hover": {
              "fill": {"value": "red"},
              "size": {"value": "280"}
            }
          }
        },
        {
          "type": "line",
          "from": {"data": "data"},
          "properties": {
            "enter": {
              "x": {"scale": "x","field": date},
              "y": {"scale": "y","field": price},
              "stroke": {"value": "blue"},
              "strokeWidth": {"value": 2}
            }
          }
        },
        {
          "type": "group",
          "from": {"data": "group"},
          "properties": {
            "update": {
              "x": {
                "scale": "x",
                "signal": "mouseDate",
                "offset": 5
              },
              "y": {
                "scale": "y",
                "signal": "mouseCount",
                "offset": -40
              },
              "width": {"value": 120},
              "height": {"value": 35},
              "fill": {"value": "#edf1f7"},
              "fillOpacity": {"value": 0.85},
              "stroke": {"value": "#aaa"},
              "strokeWidth": {"value": 0.5}
            }
          },
          "marks": [
            {
              "type": "text",
              "properties": {
                "update": {
                  "x": {"value": 6},
                  "y": {"value": 14},
                  "text": {"template": template},
                  "fill": {"value": "black"},
                  "align": {"value": "left"}
                }
              }
            },
            {
              "type": "text",
              "properties": {
                "update": {
                  "x": {"value": 6},
                  "y": {"value": 29},
                  "text": {"template": "Price: ${{parent."+price+"}}"},
                  "fill": {"value": "black"},
                  "align": {"value": "left"}
                }
              }
            }
          ]
        }
      ]
    }
  };
  return spec;
};

function makeParse(date, price) {
  var obj = {};
  obj[price] = "number";
  obj[date] = "date";
  return obj;
}

function makeTest(field, series) {
  var test;
  switch (series){
    case "daily":
      test = "year(datum."+field+") == year(mouseDate) && month(datum."+field+") == month(mouseDate) && date(datum."+field+") == date(mouseDate)";
      break;
    case "monthly":
      test = "year(datum."+field+") == year(mouseDate) && month(datum."+field+") == month(mouseDate)";
      break;
    case "annual":
      test = "year(datum."+field+") == year(mouseDate)";
      break;
  }
  return test;
}

function makeTemplate(series) {
  var template;
  switch (series){
    case "daily":
      template = "Date: {{mouseDate | time: '%Y %b %d'}}";
      break;
    case "monthly":
      template = "Date: {{mouseDate | time: '%Y %b'}}";
      break;
    case "annual":
      template = "Date: {{mouseDate | time: '%Y'}}";
      break;
  }
  return template;
}