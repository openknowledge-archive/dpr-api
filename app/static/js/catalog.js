var Catalog = {
  Models: {},
  Views: {}
};

(function(my, $) {
my.Views.Application = Backbone.View.extend({
  initialize: function () {
    var self = this;
    this.el = $(this.el);
    _.bindAll(this);
  },

  // Helpers
  // -------

  // Views
  // -------
});

my.Views.DataFile = Backbone.View.extend({
  initialize: function() {
    this.$el = $(this.el);
    _.bindAll(this);
  },

  render: function(resourceIndex) {
    var $viewer = this.$el;
    var vis = $viewer.siblings('div.vis')
    $viewer.html('Loading View <img src="http://assets.okfn.org/images/icons/ajaxload-circle.gif" />');
    vis.html('Loading View <img src="http://assets.okfn.org/images/icons/ajaxload-circle.gif" />');
    
    var table = my.dataPackageResourceToDataset(this.model.toJSON(), resourceIndex);  
    var vegaSpec = getVegaSpec(table,DataViews,resourceIndex);
    vis.empty();
    vg.embed(vis[0], vegaSpec);
    
    CSV.fetch({ 
      "url": table.localurl
    }).done(function(dataset) {
      var options = {
        data: dataset.records,
        colHeaders: dataset.fields,
        readOnly: true,
        width: 1136,
        height: function(){
          if (dataset.records.length > 16) {return 432;}
        },
        colWidths: 47,
        rowWidth: 27,
        stretchH: 'all',
        columnSorting: true,
        search: true
      };
      $viewer.empty();
      var hot = new Handsontable($viewer[0], options);
      var index = 1;
      var search = $viewer.siblings('input')[0];
      Handsontable.Dom.addEvent(search,'keyup', function (event) {
        var queryResult = hot.search.query(this.value);
        if (queryResult) {
          if (event.keyCode == 13 & index < queryResult.length) {
            // to make jump on next result on "enter" hit
            hot.selectCell(queryResult[index].row,queryResult[index].col);
            index ++;
          }else{
            // to make jumb to the first searched result
            hot.selectCell(queryResult[0].row,queryResult[0].col);
            index = 1;
          }
        }
        hot.render();
      });
    }); 
    return this;
  }
});  

my.Views.Search = Backbone.View.extend({
  events: {
    'submit .dataset-search': 'onSearchSubmit'
  },

  initialize: function() {
    this.$el = $(this.el);
  },

  onSearchSubmit: function(e) {
    var self = this;
    e.preventDefault();
    var q = $(e.target).find('input').val();
    this.model.search(q, function(error, result) {
      self.results.reset(result);
    });
  }
});

my.Models.DataFile = Backbone.Model.extend({
});

// convert a Data Package structure to a recline.Model.Dataset
my.dataPackageResourceToDataset = function(dataPackage, resourceIndex) {
  if (!resourceIndex) {
    resourceIndex = 0;
  }
  var reclineInfo = dataPackage.resources[resourceIndex];
  reclineInfo.backend = 'csv';
  // Recline expects fields at top level
  reclineInfo.fields = _.map(reclineInfo.schema.fields, function(field) {
    if (field.name && !field.id) {
      field.id = field.name;
    }
    return field;
  });
  if (reclineInfo.localurl) {
    reclineInfo.remoteurl = reclineInfo.url;
    reclineInfo.url = reclineInfo.localurl;
  }
  return reclineInfo;
};

}(Catalog, jQuery));

