# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

from flask import Blueprint, render_template, json, request, redirect, url_for
from flask import current_app as app
import jwt
from app.utils import get_zappa_prefix, get_s3_cdn_prefix
from app.site.models import Catalog
from app.package.models import User, BitStore


site_blueprint = Blueprint('site', __name__)


@site_blueprint.route("/", methods=["GET", "POST"])
def index():
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
    try:
        if request.method == "POST":
            encoded_token = request.form.get('encoded_token', '')
            if encoded_token:
                try:
                    payload = jwt.decode(encoded_token, app.config['API_KEY'])
                except Exception as e:
                    app.logger.error(e)
                    return redirect(request.headers['Host'] + '/logout')
                user = User().get_userinfo_by_id(payload['user'])
                if user:
                    return render_template("dashboard.html", user=user,
                                           title='Dashboard',
                                           zappa_env=get_zappa_prefix(),
                                           s3_cdn=get_s3_cdn_prefix()), 200
                return redirect(request.headers['Host'] + '/logout')
        return render_template("index.html", title='Home',
                               zappa_env=get_zappa_prefix(),
                               s3_cdn=get_s3_cdn_prefix(),
                               auth0_client_id=app.config['AUTH0_CLIENT_ID'],
                               auth0_domain=app.config['AUTH0_DOMAIN']), 200
    except Exception:
        return redirect(url_for('.logout'))


@site_blueprint.route("/logout", methods=["GET"])
def logout():
    """
    Loads Home page if user already login
    ---
    tags:
      - site
    responses:
      302:
        description: Load the Home Page
    """
    return render_template("logout.html", title='Home',
                           zappa_env=get_zappa_prefix(),
                           s3_cdn=get_s3_cdn_prefix(),
                           auth0_client_id=app.config['AUTH0_CLIENT_ID'],
                           auth0_domain=app.config['AUTH0_DOMAIN']), 200


@site_blueprint.route("/<publisher>/<package>", methods=["GET"])
def datapackage_show(publisher, package):
    """
    Loads datapackage page for given owner
    ---
    tags:
      - site
    parameters:
      - name: publisher
        in: path
        type: string
        required: true
        description: datapackage owner name
      - name: package
        in: path
        type: string
        description: datapackage name
    responses:
      404:
        description: Datapackage does not exist
      200:
        description: Succesfuly loaded
    """
    metadata = json.loads(
        app.test_client().\
        get('/api/package/{publisher}/{package}'.\
            format(publisher=publisher, package=package)).data)
    try:
        if metadata['error_code'] == 'DATA_NOT_FOUND':
            return "404 Not Found", 404
    except:
        pass
    catalog = Catalog(metadata)
    dataset = catalog.construct_dataset(request.url_root)
    dataViews = catalog.get_views()

    bitstore = BitStore(publisher, package)
    datapackage_json_url_in_s3 = bitstore.\
        build_s3_object_url(request.headers['Host'],
                            'datapackage.json')

    return render_template("dataset.html", dataset=dataset,
                           datapackageUrl=datapackage_json_url_in_s3,
                           showDataApi=True, jsonDataPackage=dataset,
                           dataViews=dataViews, zappa_env=get_zappa_prefix(),
                           s3_cdn=get_s3_cdn_prefix()), 200
