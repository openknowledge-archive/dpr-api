# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import json, csv
from flask import Blueprint, request, jsonify, \
    _request_ctx_stack, render_template
from flask import current_app as app
from flask import redirect, Response
from app.mod_api.models import BitStore, User, MetaDataDB
from app.utils import get_zappa_prefix, get_s3_cdn_prefix, handle_error
from app.utils.auth import requires_auth
from app.utils.auth0_helper import get_user_info_with_code, \
     get_user, update_user_secret_from_user_info
from app.utils.jwt_utilities import JWTHelper

mod_api_blueprint = Blueprint('api', __name__, url_prefix='/api')


@mod_api_blueprint.route("/package/<publisher>/<package>", methods=["PUT"])
@requires_auth
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
        user = User.query.filter_by(user_id=user_id).first()
        if user is not None:
            if user.user_name == publisher:
                metadata = BitStore(publisher=publisher,
                                      package=package,
                                      body=request.data)
                is_valid = metadata.validate()
                if not is_valid:
                    return handle_error('INVALID_DATA',
                                        'Missing required field in metadata',
                                        400)
                metadata.save()
                return jsonify({"status": "OK"}), 200
            return handle_error('NOT_PERMITTED',
                                'user name and publisher not matched',
                                403)
        return handle_error('USER_NOT_FOUND', 'user not found', 404)
    except Exception as e:
        app.logger.error(e)
        return handle_error('GENERIC_ERROR', e.message, 500)


@mod_api_blueprint.route("/package/<publisher>/<package>/finalize",
                         methods=["POST"])
@requires_auth
def finalize_metadata(publisher, package):
    """
    DPR metadata finalize operation.
    This API is responsible for getting data from S3 and push it to RDS.
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
    responses:
        200:
            description: Data transfer complete
        400:
            description: JWT is invalid
        401:
            description: Invalid Header for JWT
        403:
            description: User name and publisher not matched
        404:
            description: User not found
        500:
            description: Internal Server Error
    """
    try:
        user = _request_ctx_stack.top.current_user
        user_id = user['user']
        user = User.query.filter_by(user_id=user_id).first()
        if user is not None:
            if user.user_name == publisher:
                bit_store = BitStore(publisher, package)
                body = bit_store.get_metadata_body()
                if body is not None:
                    readme = bit_store.get_s3_object(bit_store.get_readme_object_key())
                    MetaDataDB.create_or_update(name=package, publisher=publisher,
                                                descriptor=body, readme=readme)
                    return jsonify({"status": "OK"}), 200

                raise Exception("Failed to get data from s3")
            return handle_error('NOT_PERMITTED',
                                'user name and publisher not matched',
                                403)
        return handle_error('USER_NOT_FOUND', 'user not found', 404)
    except Exception as e:
        app.logger.error(e)
        return handle_error('GENERIC_ERROR', e.message, 500)


@mod_api_blueprint.route("/package/<publisher>/<package>", methods=["GET"])
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
        data = MetaDataDB.query.filter_by(name=package,
                                          publisher=publisher).first()
        if data is None:
            return handle_error('DATA_NOT_FOUND',
                                'No metadata found for the package',
                                404)
        metadata = {
            'id': data.id,
            'name': data.name,
            'publisher': data.publisher,
            'readme': data.readme or '',
            'descriptor': json.loads(data.descriptor)
        }
        return jsonify(metadata), 200
    except Exception as e:
        return handle_error('GENERIC_ERROR', e.message, 500)


@mod_api_blueprint.route("/dataproxy/<publisher>/<package>/r/<resource>.json",
                         methods=["GET"])
@mod_api_blueprint.route("/dataproxy/<publisher>/<package>/r/<resource>.csv",
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


@mod_api_blueprint.route("/package/<publisher>", methods=["GET"])
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
        metadata = MetaDataDB.query.with_entities(MetaDataDB.name).\
            filter_by(publisher=publisher).all()
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


@mod_api_blueprint.route("/auth/callback")
def callback_handling():
    """
    This ia callback api when we redirect the api to Auth0 or any external
    Auth provider.
    ---
    tags:
        - auth
    response:
        500:
            description: Internal Server Error
        200:
            description: Updated Db with user
            schema:
                id: auth_callback
                properties:
                    status:
                        type: string
                        description: Status of the operation
                    token:
                        type: string
                        description: The jwt
                    user:
                        type: map
                        description: Returns back email, nickname,
                                     picture, name
    """
    try:
        code = request.args.get('code')
        user_info = get_user_info_with_code(code)
        user_id = user_info['user_id']

        jwt_helper = JWTHelper(app.config['API_KEY'], user_id)

        user = User().create_or_update_user_from_callback(user_info)

        return render_template("dashboard.html", user=user,
                               title='Dashboard',
                               encoded_token=jwt_helper.encode(),
                               zappa_env=get_zappa_prefix(),
                               s3_cdn=get_s3_cdn_prefix()), 200
    except Exception as e:
        app.logger.error(e)
        return handle_error('GENERIC_ERROR', e.message, 500)


@mod_api_blueprint.route("/auth/token", methods=['POST'])
def get_jwt():
    """
    This API is responsible for returning JWT token
    ---
    tags:
        - auth
    parameters:
        - in: body
          name: email
          type: string
          required: false
          description: user email id
        - in: body
          name: username
          type: string
          required: false
          description: user name
        - in: body
          name: password
          type: string
          required: true
          description: user password
    responses:
        500:
            description: Internal Server Error
        200:
            description: Success Message
            schema:
                id: put_package_success
                properties:
                    token:
                        type: string
                        description: jwt token
        400:
            description: Bad input data
        404:
            description: User not found
        403:
            description: Secret key do not match

    """
    try:
        data = request.get_json()
        user_name = data.get('username', None)
        email = data.get('email', None)
        secret = data.get('secret', None)
        verify = False
        user_id = None
        if user_name is None and email is None:
            return handle_error('INVALID_INPUT',
                                'User name or email both can not be empty',
                                400)

        if secret is None:
            return handle_error('INVALID_INPUT',
                                'secret can not be empty',
                                400)
        elif user_name is not None:
            user = User.query.filter_by(user_name=user_name).first()
            if user is None:
                return handle_error('USER_NOT_FOUND',
                                    'user does not exists',
                                    404)
            if secret == user.secret:
                verify = True
                user_id = user.user_id
        elif email is not None:
            user = User.query.filter_by(email=email).first()
            if user is None:
                return handle_error('USER_NOT_FOUND',
                                    'user does not exists',
                                    404)
            if secret == user.secret:
                verify = True
                user_id = user.user_id
        if verify:
            return jsonify({'token': JWTHelper(app.config['API_KEY'],
                                               user_id).encode()}),200
        else:
            return handle_error('SECRET_ERROR',
                                'Secret key do not match',
                                403)
    except Exception as e:
        app.logger.error(e)
        return handle_error('GENERIC_ERROR', e.message, 500)


@mod_api_blueprint.route("/auth/login", methods=['GET'])
def auth0_login():
    """
    This API is responsible for Login through external auth provider
    ---
    tags:
        - auth
    """
    redirect_url = "https://{domain}/login?client={client_id}"\
        .format(domain=app.config['AUTH0_DOMAIN'],
                client_id=app.config['AUTH0_CLIENT_ID'])
    return redirect(redirect_url)


@mod_api_blueprint.route('/auth/bitstore_upload', methods=['POST'])
def get_s3_signed_url():
    """
    This API is responsible for generate signed url to post data to S3
    ---
    tags:
        - auth
    parameters:
        - in: body
          name: publisher
          type: string
          required: true
          description: publisher name
        - in: body
          name: package
          type: string
          required: true
          description: package name
        - in: body
          name: path
          type: string
          required: true
          description: relative path of the resources
    responses:
        200:
            description: Success
            schema:
                id: get_signed_url
                properties:
                    key:
                        type: string
                        description: signed url for post data to S3
        400:
            description: Publisher or package can not be empty
        500:
            description: Internal Server Error
    """
    try:
        data = request.get_json()
        publisher = data.get('publisher', None)
        package = data.get('package', None)
        path = data.get('path', None)
        if publisher is None or package is None:
            return handle_error('INVALID_INPUT',
                                'publisher or package can not be empty',
                                400)

        metadata = BitStore(publisher=publisher, package=package)
        url = metadata.generate_pre_signed_put_obj_url(path)
        return jsonify({'key': url}), 200
    except Exception as e:
        app.logger.error(e)
        return handle_error('GENERIC_ERROR', e.message, 500)
