from flask import Blueprint, render_template, json
from flask import current_app as app

from app.utils import get_zappa_prefix, get_s3_cdn_prefix
from app.mod_site.models import Catalog

mod_site_blueprint = Blueprint('site', __name__)
catalog = Catalog()

@mod_site_blueprint.route("/", methods=["GET"])
def home():
    """
    Loads home page
    ---
    tags:
      - site
    responses:
      404:
        description: Publiser does not exist
      200:
        description: Succesfuly loaded home page
    """
    
    return render_template("index.html", title='Home', zappa_env=get_zappa_prefix(),
                           s3_cdn=get_s3_cdn_prefix()), 200

@mod_site_blueprint.route("/<owner>/<id>", methods=["GET"])
def datapackage_show(owner, id):
    """
    Loads datapackage page for given owner 
    ---
    tags:
      - site
    parameters:
      - name: owner
        in: path
        type: string
        required: true
        description: datapackage owner name
      - name: id
        in: path
        type: string
        description: datapackage name
    responses:
      404:
        description: Datapackage does not exist
      200:
        description: Succesfuly loaded
    """
    metadata = json.loads(app.test_client().get('/api/package/{owner}/{id}'.format(owner=owner, id=id)).data)
    if metadata['error_code'] == 'DATA_NOT_FOUND':
        return "404 Not Found", 404
    dataset = metadata['data']
    resources = dataset['resources']
    dataViews = dataset['views'] or []
    
    return render_template("dataset.html", dataset=dataset, showDataApi=True,
                           jsonDataPackage=dataset, dataViews=dataViews,
                           zappa_env=get_zappa_prefix(), s3_cdn=get_s3_cdn_prefix()), 200
