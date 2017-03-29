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
from app.utils import handle_error
from app.auth.annotations import check_is_authorized, get_user_from_jwt

package_blueprint = Blueprint('package', __name__, url_prefix='/api/package')


@package_blueprint.route("/<publisher>/<package>", methods=["PUT"])
@requires_auth
@is_allowed('Package::Create')
def save_metadata(publisher, package):
    """
    DPR metadata put operation.
    This API is responsible for pushing  datapackage.json to S3.
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
          description: >
            Jwt token in format of "bearer {token}.
            The token can be generated from /api/auth/token"
    responses:
        400:
            description: JWT is invalid or req body is not valid
        401:
            description: Invalid Header for JWT
        403:
            description: User name and publisher not matched
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
    try:
        user = _request_ctx_stack.top.current_user
        user_id = user['user']
        user = User.query.filter_by(id=user_id).first()
        if user is not None:
            if user.name == publisher:
                metadata = BitStore(publisher=publisher,
                                    package=package,
                                    body=request.data)
                is_valid = metadata.validate()
                if not is_valid:
                    return handle_error('INVALID_DATA',
                                        'Missing required field in metadata',
                                        400)
                metadata.save_metadata()
                return jsonify({"status": "OK"}), 200
            return handle_error('NOT_PERMITTED',
                                'user name and publisher not matched',
                                403)
        return handle_error('USER_NOT_FOUND', 'user not found', 404)
    except Exception as e:
        app.logger.error(e)
        return handle_error('GENERIC_ERROR', e.message, 500)


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
          description: >
            Jwt token in format of "bearer {token}.
            The token can be generated from /api/auth/token"
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
    try:
        data = request.get_json()
        if 'version' not in data:
            return handle_error('ATTRIBUTE_MISSING', 'version not found', 400)

        bitstore = BitStore(publisher, package)
        status_db = Package.create_or_update_tag(publisher, package, data['version'])
        status_bitstore = bitstore.copy_to_new_version(data['version'])

        if status_db is False or status_bitstore is False:
            raise Exception("failed to tag data package")
        return jsonify({"status": "OK"}), 200
    except Exception as e:
        app.logger.error(e)
        return handle_error('GENERIC_ERROR', e.message, 500)


@package_blueprint.route("/<publisher>/<package>", methods=["DELETE"])
@is_allowed('Package::Delete')
def delete_data_package(publisher, package):
    """
    DPR data package soft delete operation.
    This API is responsible for mark for delete of data package
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
          description: >
            Jwt token in format of "bearer {token}.
            The token can be generated from /api/auth/token"
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
    try:
        bitstore = BitStore(publisher=publisher, package=package)
        status_acl = bitstore.change_acl('private')
        status_db = Package.change_status(publisher, package)
        if status_acl and status_db:
            return jsonify({"status": "OK"}), 200
        if not status_acl:
            raise Exception('Failed to change acl')
        if not status_db:
            raise Exception('Failed to change status')
    except Exception as e:
        app.logger.error(e)
        return handle_error('GENERIC_ERROR', e.message, 500)


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
          description: >
            Jwt token in format of "bearer {token}.
            The token can be generated from /api/auth/token"
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
    try:
        bitstore = BitStore(publisher=publisher, package=package)
        status_acl = bitstore.change_acl('public-read')
        status_db = Package.change_status(publisher, package, PackageStateEnum.active)
        if status_acl and status_db:
            return jsonify({"status": "OK"}), 200
        if not status_acl:
            raise Exception('Failed to change acl')
        if not status_db:
            raise Exception('Failed to change status')
    except Exception as e:
        app.logger.error(e)
        return handle_error('GENERIC_ERROR', e.message, 500)


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
          description: >
            Jwt token in format of "bearer {token}.
            The token can be generated from /api/auth/token"
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
    try:
        bitstore = BitStore(publisher=publisher, package=package)
        status_acl = bitstore.delete_data_package()
        status_db = Package.delete_data_package(publisher, package)
        if status_acl and status_db:
            return jsonify({"status": "OK"}), 200
        if not status_acl:
            raise Exception('Failed to delete from s3')
        if not status_db:
            raise Exception('Failed to delete from db')
    except Exception as e:
        app.logger.error(e)
        return handle_error('GENERIC_ERROR', e.message, 500)


@package_blueprint.route("/upload", methods=["POST"])
@requires_auth
def finalize_publish():
    """
    Data package finalize operation.
    This API is responsible for getting the Data Package (datapackage.json, README)
    and importing it into our MetaStore.
    ---
    tags:
        - package
    parameters:
        - in: body
          type: map
          required: true
          description: data package url
        - in: header
          name: Authorization
          type: string
          required: true
          description: >
            Jwt token in format of "{token}.
            The token can be generated from /api/auth/token"
    responses:
        200:
            description: Data transfer complete
        400:
            description: UN-AUTHORIZE
        401:
            description: Invalid Header for JWT
        500:
            description: Internal Server Error
    """
    try:
        data = request.get_json()
        datapackage_url = data['datapackage']
        publisher, package, version = BitStore.extract_information_from_s3_url(datapackage_url)
        user_id = None
        jwt_status, user_info = get_user_from_jwt(request, app.config['API_KEY'])
        if jwt_status:
            user_id = user_info['user']

        if Package.is_package_exists(publisher, package):
            status = check_is_authorized('Package::Update', publisher, package, user_id)
        else:
            status = check_is_authorized('Package::Create', publisher, package, user_id)

        if not status:
            return handle_error('UN-AUTHORIZE', 'not authorized to upload data', 400)

        bit_store = BitStore(publisher, package)
        b = bit_store.get_metadata_body()
        body = json.loads(b)
        if body is not None:
            bit_store.change_acl('public-read')
            readme = bit_store.get_s3_object(bit_store.get_readme_object_key())
            Package.create_or_update(name=package, publisher_name=publisher,
                                     descriptor=body, readme=readme)
            return jsonify({"status": "queued"}), 200

        raise Exception("Failed to get data from s3")

    except Exception as e:
        app.logger.error(e)
        return handle_error('GENERIC_ERROR', e.message, 500)


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
    try:
        data = Package.query.join(Publisher).\
            filter(Publisher.name == publisher,
                   Package.name == package,
                   Package.status == PackageStateEnum.active).\
            first()
        if data is None:
            return handle_error('DATA_NOT_FOUND',
                                'No metadata found for the package',
                                404)
        tag = filter(lambda t: t.tag == 'latest', data.tags)[0]
        metadata = {
            'id': data.id,
            'name': data.name,
            'publisher': data.publisher.name,
            'readme': tag.readme or '',
            'descriptor': tag.descriptor
        }
        return jsonify(metadata), 200
    except Exception as e:
        return handle_error('GENERIC_ERROR', e.message, 500)


@package_blueprint.route("/dataproxy/<publisher>/<package>/r/<resource>.json",
                         methods=["GET"])
@package_blueprint.route("/dataproxy/<publisher>/<package>/r/<resource>.csv",
                         methods=["GET"])
def get_resource(publisher, package, resource):
    """
    DPR resource get operation.
    This API is responsible for getting resource from S3.
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
          description: package name - to retrieve the data package metadata
        - in: path
          name: resource
          type: string
          required: true
          description: resource index or name
    responses:

        200:
            description: Get Data package for one key
            schema:
                id: get_data_package
                properties:
                    data:
                        type: string
                        description: The resource
        500:
            description: Internal Server Error
    """
    try:
        path = request.path
        metadata = BitStore(publisher, package)
        if path.endswith('csv'):
            resource_key = metadata.build_s3_key(resource + '.csv')
            data = metadata.get_s3_object(resource_key)

            def generate():
                for row in data.splitlines():
                    yield row + '\n'
            return Response(generate()), 200
        else:
            resource_key = metadata.build_s3_key(resource + '.csv')
            data = metadata.get_s3_object(resource_key)
            data = csv.DictReader(data.splitlines())
            # taking first and adding at the end to avoid last comma
            first_row = next(data)

            def generate():
                yield '['
                for row in data:
                    yield json.dumps(row) + ','
                yield json.dumps(first_row)+']'
            return Response(generate(), content_type='application/json'), 200
    except Exception as e:
        return handle_error('GENERIC_ERROR', e.message, 500)


@package_blueprint.route("/<publisher>", methods=["GET"])
def get_all_metadata_names_for_publisher(publisher):
    """
    DPR meta-data get operation.
    This API is responsible for getting All keys for the publisher
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
                            type: string
                        description: All data package names for the publisher
        500:
            description: Internal Server Error
        404:
            description: No metadata found for the package
    """
    try:
        metadata = Package.query.join(Publisher).\
            with_entities(Package.name).\
            filter(Publisher.name == publisher).all()
        if len(metadata) is 0:
            return handle_error('DATA_NOT_FOUND',
                                'No metadata found for the package',
                                404)
        keys = []
        for d in metadata:
            keys.append(d[0])
        return jsonify({'data': metadata}), 200
    except Exception as e:
        app.logger.error(e)
        return handle_error('GENERIC_ERROR', e.message, 500)
