from functools import wraps
import requests
from flask import Blueprint, render_template, json, jsonify, redirect, request
from flask import current_app as app
from flask import url_for

from app.mod_site.models import Catalog

mod_site = Blueprint('site', __name__)

datapackage = json.loads(open('fixtures/datapackage.json').read())
datapackage['owner'] = 'demo'
catalog = Catalog()
catalog.load([datapackage])


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get('Authorization', None)
        if not auth:
            return redirect(app.config['AUTH0_LOGIN_PAGE'])
    return decorated


@mod_site.route("/api/callback")
def callback_handling():
    code = request.args.get('code')

    json_header = {'content-type': 'application/json'}

    token_url = "https://{domain}/oauth/token".format(domain=app.config["AUTH0_DOMAIN"])
    token_payload = {
        'client_id': app.config['AUTH0_CLIENT_ID'],
        'client_secret': app.config['AUTH0_CLIENT_SECRET'],
        'redirect_uri': app.config['AUTH0_CALLBACK_URL'],
        'code': code,
        'grant_type': 'authorization_code'
        }

    token_info = requests.post(token_url, data=json.dumps(token_payload), headers=json_header).json()
    print token_info
    user_url = "https://{domain}/userinfo?access_token={access_token}" \
        .format(domain=app.config["AUTH0_DOMAIN"], access_token=token_info['access_token'])

    user_info = requests.get(user_url).json()
    return redirect(url_for('site.home'))


@mod_site.route("/", methods=["GET"])
@mod_site.route("/home", methods=["GET"])
def home():
    """
    Loads home page
    ---
    tags:
      - site
    responses:
      200:
        description: Succesfuly loaded home page
    """
    datasets = catalog.query()
    coreDatasets = catalog.by_owner('core')
    total = len(datasets)
    return render_template("index.html", total=total, datasets= datasets, coreDatasets=coreDatasets, title= 'home'), 200

@mod_site.route("/<owner>/<id>", methods=["GET"])
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
    dataset = catalog.get(owner, id)
    if not dataset:
        return "404 Not Found"
    resources = dataset['resources']
    for idx in range(len(resources)):
        resource_name = resources[idx]['name'] or idx
        dataset['resources'][idx]['localurl'] = '/' + owner + '/' + id + '/r/' + resource_name + '.csv'
    dataViews = dataset['views'] or []
    return render_template("dataset.html", dataset= dataset, showDataApi=True, jsonDataPackage=dataset, dataViews=dataViews)