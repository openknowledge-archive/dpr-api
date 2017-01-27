# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from flask import Blueprint, request, jsonify
from flask import current_app as app
from app.utils import handle_error
from app.search.models import DataPackageQuery

search_blueprint = Blueprint('search', __name__, url_prefix='/api/search')


@search_blueprint.route("/package", methods=["GET"])
def search_packages():
    """
        DPR metadata put operation.
        This API is responsible for searching data package
        ---
        tags:
            - search
        parameters:
            - in: query
              name: q
              type: string
              required: true
              description: search query string e.g. q=query publisher=pub
        responses:
            500:
                description: Internal Server Error
            200:
                description: Success Message
                schema:
                    id: search_package_success
                    properties:
                        status:
                            type: string
                            description: Status of the operation
                            default: SUCCESS
                        data:
                            type: list
                            properties:
                                type: object
                                properties:
                                    name:
                                        type: string
                                    title:
                                        type: string
                                    description:
                                        type: string

        """
    try:
        q = request.args.get('q')
        result = DataPackageQuery(query_string=q).get_data()

        return jsonify(dict(data=result, status='SUCCESS'))
    except Exception as e:
        app.logger.error(e)
        return handle_error('GENERIC_ERROR', e.message, 500)
