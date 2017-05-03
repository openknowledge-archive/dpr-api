# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import csv
import json

from flask import Blueprint, request, jsonify, \
    _request_ctx_stack
from flask import current_app as app
from flask import Response

from app.package.models import BitStore, Package, PackageStateEnum
from app.profile.models import Publisher, User
from app.auth.annotations import requires_auth, is_allowed
from app.utils import InvalidUsage
from app.auth.annotations import check_is_authorized, get_user_from_jwt

package_blueprint = Blueprint('package', __name__, url_prefix='/api/package')


@package_blueprint.route("/<publisher>/<package>/tag", methods=["POST"])
@requires_auth
@is_allowed('Package::Update')
def tag_data_package(publisher, package):
    """
    DPR metadata put operation.
    This API is responsible for tagging data package
    ---
    tags:
        - package
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
        - in: body
          name: version
          type: string
          required: true
          description: version value
        - in: header
          name: Authorization
          type: string
          required: true
          description: JWT Token
    responses:
        400:
            description: JWT is invalid or req body is not valid
        401:
            description: Invalid Header for JWT
        403:
            description: User not allowed for operation
        404:
            description: User not found
        500:
            description: Internal Server Error
        200:
            description: Success Message
            schema:
                id: put_package_success
                properties:
                    status:
                        type: string
                        description: Status of the operation
                        default: OK
    """
    data = request.get_json()
    if 'version' not in data:
        raise InvalidUsage('version not found', 400)

    bitstore = BitStore(publisher, package)
    status_db = Package.create_or_update_tag(publisher, package, data['version'])
    try:
        status_bitstore = bitstore.copy_to_new_version(data['version'])
    except Exception as e:
        ## TODO roll back changes in db
        raise InvalidUsage(e.message, 500)

    return jsonify({"status": "OK"}), 200


@package_blueprint.route("/<publisher>/<package>", methods=["DELETE"])
@is_allowed('Package::Delete')
def delete_data_package(publisher, package):
    """
    DPR Data Package Soft Delete
    Marks Data Package as private
    ---
    tags:
        - package
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
        - in: header
          name: Authorization
          type: string
          required: true
          description: JWT Token
    responses:
        500:
            description: Internal Server Error
        200:
            description: Success Message
            schema:
                id: put_package_success
                properties:
                    status:
                        type: string
                        default: OK
    """
    bitstore = BitStore(publisher=publisher, package=package)
    status_db = Package.change_status(publisher, package, PackageStateEnum.deleted)
    try:
        status_acl = bitstore.change_acl('private')
    except Exception as e:
        ## TODO roll back changes in db
        raise InvalidUsage(e.message, 500)
    if status_acl and status_db:
        return jsonify({"status": "OK"}), 200


@package_blueprint.route("/<publisher>/<package>/undelete", methods=["POST"])
@requires_auth
@is_allowed('Package::Undelete')
def undelete_data_package(publisher, package):
    """
    DPR data package un-delete operation.
    This API is responsible for un-mark the mark for delete of data package
    ---
    tags:
        - package
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
        - in: header
          name: Authorization
          type: string
          required: true
          description: JWT Token
    responses:
        500:
            description: Internal Server Error
        200:
            description: Success Message
            schema:
                id: put_package_success
                properties:
                    status:
                        type: string
                        default: OK

    """
    bitstore = BitStore(publisher=publisher, package=package)
    status_db = Package.change_status(publisher, package, PackageStateEnum.active)
    try:
        status_acl = bitstore.change_acl('public-read')
    except Exception as e:
        ## TODO roll back changes in db
        raise InvalidUsage(e.message, 500)
    if status_acl and status_db:
        return jsonify({"status": "OK"}), 200


@package_blueprint.route("/<publisher>/<package>/purge", methods=["DELETE"])
@requires_auth
@is_allowed('Package::Purge')
def purge_data_package(publisher, package):
    """
    DPR data package hard delete operation.
    This API is responsible for deletion of data package
    ---
    tags:
        - package
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
        - in: header
          name: Authorization
          type: string
          required: true
          description: JWT Token
    responses:
        500:
            description: Internal Server Error
        200:
            description: Success Message
            schema:
                id: put_package_success
                properties:
                    status:
                        type: string
                        default: OK
    """
    bitstore = BitStore(publisher=publisher, package=package)
    status_db = Package.delete_data_package(publisher, package)
    try:
        status_acl = bitstore.delete_data_package()
    except Exception as e:
        ## TODO roll back changes in db
        raise InvalidUsage(e.message, 500)
    if status_acl and status_db:
        return jsonify({"status": "OK"}), 200

@package_blueprint.route("/upload", methods=["POST"])
@requires_auth
def finalize_publish():
    """
    Data Package finalize operation.

    Gets the datapackage.json and README for Data Package and imports into database.
    ---
    tags:
        - package
    parameters:
        - in: body
          name: url
          type: map
          required: true
          description: URL to bitstore (S3) for Data Package.
        - in: header
          name: Authorization
          type: string
          required: true
          description: JWT Token
    responses:
        200:
            description: Data Uploaded
        400:
            description: Un-Authorized
        401:
            description: Invalid Header For JWT
        500:
            description: Internal Server Error
    """
    data = request.get_json()
    datapackage_url = data['datapackage']
    publisher, package, version = BitStore.extract_information_from_s3_url(datapackage_url)
    user_id = None
    jwt_status, user_info = get_user_from_jwt(request, app.config['JWT_SEED'])
    if jwt_status:
        user_id = user_info['user']

    if Package.is_package_exists(publisher, package):
        status = check_is_authorized('Package::Update', publisher, package, user_id)
    else:
        status = check_is_authorized('Package::Create', publisher, package, user_id)

    if not status:
        raise InvalidUsage('Not authorized to upload data', 400)

    bit_store = BitStore(publisher, package)
    b = bit_store.get_metadata_body()
    body = json.loads(b)
    if body is not None:
        bit_store.change_acl('public-read')
        readme = bit_store.get_s3_object(bit_store.get_readme_object_key())
        Package.create_or_update(name=package, publisher_name=publisher,
                                 descriptor=body, readme=readme)
        return jsonify({"status": "queued"}), 200

    raise InvalidUsage("Failed to get data from s3")


@package_blueprint.route("/<publisher>/<package>", methods=["GET"])
def get_metadata(publisher, package):
    """
    DPR meta-data get operation.
    This API is responsible for getting datapackage.json from S3.
    ---
    tags:
        - package
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
          description: package name - to retrieve the data package metadata
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
            description: Internal Server Error
        404:
            description: No metadata found for the package
    """
    data = Package.query.join(Publisher).\
        filter(Publisher.name == publisher,
               Package.name == package,
               Package.status == PackageStateEnum.active).\
        first()
    if data is None:
        raise InvalidUsage('No metadata found for the package', 404)
    tag = filter(lambda t: t.tag == 'latest', data.tags)[0]
    metadata = {
        'id': data.id,
        'name': data.name,
        'publisher': data.publisher.name,
        'readme': tag.readme or '',
        'descriptor': tag.descriptor
    }
    return jsonify(metadata), 200


@package_blueprint.route("/<publisher>", methods=["GET"])
def get_all_metadata_names_for_publisher(publisher):
    """
    Get Packages For Publisher
    Returns all packages published under given publisher
    ---
    tags:
        - package
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
                            type: array
                            items:
                                type: string
        500:
            description: Internal Server Error
        404:
            description: No Data Package Found For The Publisher
    """
    metadata = Package.query.join(Publisher).\
        with_entities(Package.name).\
        filter(Publisher.name == publisher).all()
    if len(metadata) is 0:
        raise InvalidUsage('No Data Package Found For The Publisher', 404)
    keys = []
    for d in metadata:
        keys.append(d[0])
    return jsonify({'data': metadata}), 200
