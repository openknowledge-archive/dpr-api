# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

from flask import Blueprint, render_template, \
    json, request, redirect, url_for, make_response
from flask import current_app as app
from app.auth.models import JWT
from app.site.models import Catalog
from app.package.models import BitStore
from app.profile.models import User, Publisher
from app.search.models import DataPackageQuery
from markdown import markdown
from BeautifulSoup import BeautifulSoup

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
    user, exception = get_user_from_cookie()
    if user:
        return render_template("dashboard.html",
                               user=user,
                               title='Dashboard'), 200
    if exception:
        return redirect(request.headers['Host'] + '/logout')
    return render_template("index.html", title='Home'), 200


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
    resp = make_response(render_template("logout.html", title='Logout'), 200)
    resp.set_cookie('jwt', '', expires=0)
    return resp


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
    user, exception = get_user_from_cookie()
    if exception:
        return redirect(request.headers['Host'] + '/logout')

    metadata = json.loads(
        app.test_client(). \
            get('/api/package/{publisher}/{package}'. \
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
    datapackage_json_url_in_s3 = bitstore. \
        build_s3_object_url(request.headers['Host'],
                            'datapackage.json')
    readme_short_markdown = markdown(metadata.get('readme', ''))
    readme_short = ''.join(BeautifulSoup(readme_short_markdown).findAll(text=True)) \
        .split('\n\n')[0].replace(' \n', '') \
        .replace('\n', ' ').replace('/^ /', '')

    return render_template("dataset.html", user=user,
                           dataset=dataset,
                           datapackageUrl=datapackage_json_url_in_s3,
                           showDataApi=True, jsonDataPackage=dataset,
                           dataViews=dataViews,
                           readmeShort=readme_short
                           ), 200


@site_blueprint.route("/<publisher>", methods=["GET"])
def publisher_dashboard(publisher):
    user, exception = get_user_from_cookie()
    if exception:
        return redirect(request.headers['Host'] + '/logout')

    datapackage_list = DataPackageQuery(query_string="* publisher:{publisher}"
                                        .format(publisher=publisher)).get_data()
    publisher = Publisher.get_publisher_info(publisher)

    return render_template("publisher.html",
                           user=user,
                           publisher=publisher,
                           datapackage_list=datapackage_list), 200


@site_blueprint.route("/search", methods=["GET"])
def search_package():
    user, exception = get_user_from_cookie()
    q = request.args.get('q')
    if q is None:
        q = ''
    datapackage_list = DataPackageQuery(query_string=q.strip()).get_data(20)
    return render_template("search.html", user=user,
                           datapackage_list=datapackage_list,
                           total_count=len(datapackage_list),
                           query_term=q), 200


def get_user_from_cookie():
    token = request.cookies.get('jwt')
    user, exception = None, None
    if token:
        try:
            payload = JWT(app.config['API_KEY']).decode(token)
            user = User().get_userinfo_by_id(payload['user'])
        except Exception as e:
            app.logger.error(e)
            exception = e
    return user, exception
