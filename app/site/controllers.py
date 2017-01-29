# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

from flask import Blueprint, render_template, send_from_directory

site_blueprint = Blueprint('site', __name__)


@site_blueprint.route("/", methods=["GET"])
def index():
    """
    Loads home page
    ---
    tags:
      - site
    responses:
      200:
        description: Succesfuly loaded home page
    """
    return render_template("index.html"), 200


@site_blueprint.route("/static/<file_name>", methods=['GET'])
def server_static(file_name):
    """
     Serves static files
    ---
    tags:
      - site
    responses:
      200:
        description: Succesfuly loaded home page
    """
    return send_from_directory('static', file_name)
