# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from flask import Blueprint, jsonify
from flask import current_app as app
from app.logic import get_publisher
from app.profile.models import Publisher
from app.schemas import PublisherSchema
from app.utils import InvalidUsage

profile_blueprint = Blueprint('profile', __name__, url_prefix='/api/profile')


@profile_blueprint.route("/publisher/<name>", methods=['GET'])
def get_publisher_profile(name):
    """
        DPR metadata put operation.
        This API is responsible for getting publisher profile
        ---
        tags:
            - profile
        parameters:
            - in: path
              name: publisher
              type: string
              required: true
              description: publisher name
        responses:
            404:
                description: Publisher not found
            500:
                description: Internal Server Error
            200:
                description: Success Message
                schema:
                    id: get_package_success
                    properties:
                        data:
                            type: object
                            description: data of publisher profile
                            properties:
                                description:
                                  type: string
                                title:
                                  type: string
                                name:
                                  type: string
                                joined:
                                  type: string
                                contact:
                                    type: object
                                    properties:
                                        phone:
                                            type: string
                                        email:
                                            type: string
                                        country:
                                            type: string

                        status:
                            type: string
                            default: SUCCESS
        """
    info = get_publisher(name)
    return jsonify(dict(data=info, status="SUCCESS"))
