import json
from flask import Blueprint, request, jsonify
from flask import current_app as app
from app.mod_api.models import MetaDataS3, MetaDataDB
from app.database import s3, db

mod_api = Blueprint('api', __name__, url_prefix='/api')


@mod_api.route("/<publisher>/<package>", methods=["PUT"])
def save_metadata(publisher, package):
    """
    DPR metadata put operation.
    This API is responsible for pushing  datapackage.json to S3.
    ---
    tags:
        - metadata
    parameters:
        - in: path
          name: publisher
          type: string
          required: true
          description: publisher name
        - in: path
          name: package
          type: string
          required: true
          description: package name
    responses:
        500:
            description: Error Message
            schema:
                id: put_package_error
                properties:
                    status:
                        type: string
                        description: Status of the operation
                    message:
                        type: string
                        description: Exception message
        200:
            description: Success Message
            schema:
                id: put_package_success
                properties:
                    status:
                        type: string
                        description: Status of the operation
    """
    try:
        metadata = MetaDataS3(publisher=publisher, package=package, body=request.data)
        metadata.save()
        return jsonify({"status": "OK"}), 200
    except Exception as e:

        return jsonify({'status': 'KO', 'message': e.message}), 500


@mod_api.route("/<publisher>/<package>", methods=["GET"])
def get_metadata(publisher, package):
    """
    DPR meta-data get operation.
    This API is responsible for getting datapackage.json from S3.
    ---
    tags:
        - metadata
    parameters:
        - in: path
          name: publisher
          type: string
          required: true
          description: publisher name
        - in: path
          name: package
          type: string
          required: false
          description: package name, use this to retrieve the data package metadata contents
    responses:

        200:
            description: Get Data package for one key
            schema:
                id: get_data_package
                properties:
                    data:
                        type: map
                        description: The datapackage.json
        500:
            description: Error Message
            schema:
                id: get_package_error
                properties:
                    status:
                        type: string
                        description: Status of the operation
                    message:
                        type: string
                        description: Exception message
    """
    try:
        metadata = MetaDataDB.query.filter_by(name=package, publisher=publisher).first().descriptor
        return jsonify({"data": metadata, "status": "OK"}), 200
    except Exception as e:
        app.logger.error(e)
        return jsonify({'status': 'KO', 'message': e.message}), 500


@mod_api.route("/<publisher>", methods=["GET"])
def get_all_metadata_names_for_publisher(publisher):
    """
    DPR meta-data get operation.
    This API is responsible for getting All keys for the publisher
    ---
    tags:
        - metadata
    parameters:
        - in: path
          name: publisher
          type: string
          required: true
          description: publisher name
    responses:
        200:
            description: Get Data package for one key
            schema:
                id: get_data_package
                properties:
                    data:
                        type: array
                        items:
                            type: string
                        description: All data package names for the publisher
        500:
            description: Error Message
            schema:
                id: get_package_error
                properties:
                    status:
                        type: string
                        description: Status of the operation
                    message:
                        type: string
                        description: Exception message
    """
    try:
        metadata = MetaDataS3(publisher=publisher)
        keys = metadata.get_all_metadata_name_for_publisher()
        return jsonify({'data': keys, "status": "OK"}), 200
    except Exception as e:
        app.logger.error(e)
        return jsonify({'status': 'KO', 'message': e.message}), 500
