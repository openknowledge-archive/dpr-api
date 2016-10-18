from flask import Blueprint, render_template, json, jsonify
from flask import current_app as app
from app.mod_site.models import Catalog

mod_site = Blueprint('site', __name__)
datapackage = json.loads(open('fixtures/datapackage.json').read())
datapackage['owner'] = 'demo'
catalog = Catalog()
catalog.load([datapackage])

@mod_site.route("/", methods=["GET"])
def home():
    datasets = catalog.query()
    coreDatasets = catalog.by_owner('core')
    total = len(datasets)
    return render_template("index.html", total=total, datasets= datasets, coreDatasets=coreDatasets, title= 'home')

@mod_site.route("/<owner>/<id>", methods=["GET"])
def datapackage_show(owner, id):
    dataset = catalog.get(owner, id)
    if not dataset:
        return "404 Not Found"
    resources = dataset['resources']
    for idx in range(len(resources)):
        resource_name = resources[idx]['name'] or idx
        dataset['resources'][idx]['localurl'] = '/' + owner + '/' + id + '/r/' + resource_name + '.csv'
    dataViews = dataset['views'] or []
    return render_template("dataset.html", dataset= dataset, showDataApi=True, jsonDataPackage=dataset, dataViews=dataViews)