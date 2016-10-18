var getVegaSpec = function(table,DataViews,resourceIndex) {
  var price = DataViews[resourceIndex].state.series[0];
  var date = DataViews[resourceIndex].state.group;
  var parse = makeParse(date, price);
  // needs to be automate (passed to datapackage.json or smth)
  var template = makeTemplate(date, "daily");
  var spec = {
    "actions": false,
    "spec": {
      "width": 1080,
      "height": 500,
      "signals": [
        {
          "name": "tooltip",
          "init": {},
          "streams": [
            {"type": "symbol:mouseover", "expr": "datum"},
            {"type": "symbol:mouseout", "expr": "{}"}
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
          "type": "text",
          "properties": {
            "enter": {
              "align": {"value": "left"},
              "fill": {"value": "#333"}
            },
            "update": {
              "x": {"scale": "x", "signal": "tooltip."+date, "offset": 15},
              "y": {"scale": "y", "signal": "tooltip."+price, "offset": -20},
              "text": {"template": template},
              "fillOpacity": [
                { "test": "!tooltip._id",
                  "value": 0
                },
                {"value": 1}
              ]
            }
          }
        },
        {
          "type": "text",
          "properties": {
            "enter": {
              "align": {"value": "left"},
              "fill": {"value": "#333"}
            },
            "update": {
              "x": {"scale": "x", "signal": "tooltip."+date, "offset": 15},
              "y": {"scale": "y", "signal": "tooltip."+price, "offset": -5},
              "text": {"signal": "tooltip."+price},
              "fillOpacity": [
                { "test": "!tooltip._id",
                  "value": 0
                },
                {"value": 1}
              ]
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

function makeTemplate(field, series) {
  var template;
  switch (series){
    case "daily":
      template = "Date: {{tooltip."+field+"| time: '%Y %b %d'}}";
      break;
    case "monthly":
      template = "Date: {{tooltip."+field+"| time: '%Y %b'}}";
      break;
    case "annual":
      template = "Date: {{tooltip."+field+"| time: '%Y'}}";
      break;
  }
  return template;
}