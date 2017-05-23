# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

from flask import Blueprint, render_template, \
    json, request, redirect, g, make_response
from flask import current_app as app
from app.auth.jwt import JWT
from app.bitstore import BitStore
from app.utils import InvalidUsage
import app.logic as logic

site_blueprint = Blueprint('site', __name__)


@site_blueprint.route("/", methods=["GET", "POST"])
def index():
    """
    Renders index.html if no token found in cookie.
    If token found in cookie then it renders dashboard.html
    """
    showcase_packages = [logic.Package.get(item['publisher'], item['package']) for item in app.config['FRONT_PAGE_SHOWCASE_PACKAGES']]
    tutorial_packages = [ logic.Package.get(item['publisher'], item['package']) for item in app.config['TUTORIAL_PACKAGES']]
    showcase_packages = filter(None, showcase_packages)
    tutorial_packages = filter(None, tutorial_packages)

    if g.current_user:
        return render_template("dashboard.html",
                               title='Dashboard'), 200
    return render_template("index.html",
                            title='Home',
                            showcase_packages=showcase_packages,
                            tutorial_packages=tutorial_packages), 200


@site_blueprint.route("/logout", methods=["GET"])
def logout():
    """
    Sets blank cookie value with expiry time zero
    and renders logout.html page
    """
    g.current_user = None
    resp = make_response(render_template("logout.html", title='Logout'), 200)
    resp.set_cookie('jwt', '', expires=0)
    return resp


@site_blueprint.route("/<publisher>/<package>", methods=["GET"])
def datapackage_show(publisher, package):
    """
    Loads datapackage page for given owner
    """
    datapackage = logic.Package.get(publisher, package)
    if not datapackage:
        raise InvalidUsage("Page Not Found", 404)

    return render_template("dataset.html",
                           dataset=datapackage.get('descriptor'),
                           datapackageUrl=datapackage.get('datapackag_url'),
                           showDataApi=True,
                           dataViews=datapackage.get('views'),
                           readmeShort=datapackage.get('short_readme'),
                           readme_long=datapackage.get('readme')
                           ), 200


@site_blueprint.route("/<publisher>", methods=["GET"])
def publisher_dashboard(publisher):
    datapackage_list = logic.search.DataPackageQuery(query_string="* publisher:{publisher}"
                                        .format(publisher=publisher)).get_data()

    publisher = logic.Publisher.get(publisher)
    if not publisher:
        raise InvalidUsage('Not Found', 404)
    return render_template("publisher.html",
                           publisher=publisher,
                           datapackage_list=datapackage_list), 200


@site_blueprint.route("/search", methods=["GET"])
def search_package():
    q = request.args.get('q')
    if q is None:
        q = ''
    datapackage_list = logic.search.DataPackageQuery(query_string=q.strip(),
                                        limit=1000).get_data()
    return render_template("search.html",
                           datapackage_list=datapackage_list,
                           total_count=len(datapackage_list),
                           query_term=q), 200
