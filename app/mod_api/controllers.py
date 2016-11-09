import json
from flask import Blueprint, request, jsonify, _request_ctx_stack, render_template
from flask import current_app as app
from flask import redirect
from app.database import db
from app.mod_api.models import MetaDataS3, User, MetaDataDB
from app.utils import get_zappa_prefix, get_s3_cdn_prefix
from app.utils.auth import requires_auth
from app.utils.auth0_helper import get_user_info_with_code, \
    update_user_secret, get_user, update_user_secret_from_user_info
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
        user = _request_ctx_stack.top.current_user
        user_id = user['user']
        user = User.query.filter_by(user_id=user_id).first()
        if user is not None:
            if user.user_name == publisher:
                metadata = MetaDataS3(publisher=publisher, package=package, body=request.data)
                is_valid = metadata.validate()
                if not is_valid:
                    return jsonify(
                        {"error_code": "INVALID_DATA", "message": 'Missing required field in metadata'}), 400
                metadata.save()
                return jsonify({"status": "OK"}), 200
            return jsonify({"error_code": "USER_NOT_FOUND", "message": 'user name and publisher not matched'}), 400
        return jsonify({"error_code": "USER_NOT_FOUND", "message": 'user not found'}), 404
    except Exception as e:
        app.logger.error(e)
        return jsonify({'error_code': 'GENERIC_ERROR', 'message': e.message}), 500


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
        data = MetaDataDB.query.filter_by(name=package, publisher=publisher).first()
        if data is None:
            return jsonify({"message": 'No metadata found for the package', "error_code": "DATA_NOT_FOUND"}), 404
        metadata = json.loads(data.descriptor)
        return jsonify({"data": metadata}), 200
    except Exception as e:
        return jsonify({'error_code': 'GENERIC_ERROR', 'message': e.message}), 500


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
        metadata = MetaDataDB.query.with_entities(MetaDataDB.name).filter_by(publisher=publisher).all()
        if len(metadata) is 0:
            return jsonify({'error_code': 'DATA_NOT_FOUND', "status": "OK"}), 404
        keys = []
        for d in metadata:
            keys.append(d[0])
        return jsonify({'data': metadata, "status": "OK"}), 200
    except Exception as e:
        app.logger.error(e)
        return jsonify({'error_code': 'GENERIC_ERROR', 'message': e.message}), 500


@mod_api_blueprint.route("/auth/callback")
def callback_handling():
    """
    This ia callback api when we redirect the api to Auth0 or any external
    Auth provider.
    ---
    tags:
        - auth
    response:
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
                        description: Returns back email, nickname, picture, name
    """
    try:
        code = request.args.get('code')
        user_info = get_user_info_with_code(code)
        user_id = user_info['user_id']
        update_user_secret_from_user_info(user_info)

        user_info = get_user(user_id)
        jwt_helper = JWTHelper(app.config['API_KEY'], user_id)

        user = User().create_or_update_user_from_callback(user_info)

        ## For now dashboard is rendered directly from callbacl, this needs to be changed
        return render_template("dashboard.html", user=user.serialize['name'],
                               zappa_env=get_zappa_prefix(), s3_cdn=get_s3_cdn_prefix()), 200
        # return jsonify({'status': 'OK', 'token': jwt_helper.encode(), 'user': user.serialize}), 200
    except Exception as e:
        app.logger.error(e)
        return jsonify({'error_code': 'GENERIC_ERROR', 'message': e.message}), 500


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
            description: Generic Error
            schema:
                id: generic_error
                properties:
                    error_code:
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
                    token:
                        type: string
                        description: jwt token
        400:
            description: Bad input data
            schema:
                id:
    """
    try:
        data = request.get_json()
        user_name = data.get('username', None)
        email = data.get('email', None)
        secret = data.get('secret', None)
        verify = False
        user_id = None
        if user_name is None and email is None:
            return jsonify({'message': 'User name or email both can not be empty',
                            'error_code': 'INVALID_INPUT'}), 400

        if secret is None:
            return jsonify({'message': 'secret can not be empty', 'error_code': 'INVALID_INPUT'}), 400
        elif user_name is not None:
            user = User.query.filter_by(user_name=user_name).first()
            if user is None:
                return jsonify({'message': 'user does not exists', 'error_code': 'USER_NOT_FOUND'}), 404
            if secret == user.secret:
                verify = True
                user_id = user.user_id
        elif email is not None:
            user = User.query.filter_by(email=email).first()
            if user is None:
                return jsonify({'message': 'user does not exists', 'error_code': 'USER_NOT_FOUND'}), 404
            if secret == user.secret:
                verify = True
                user_id = user.user_id
        if verify:
            return jsonify({'token': JWTHelper(app.config['API_KEY'], user_id).encode()}), 200
        else:
            return jsonify({'message': 'Secret key do not match', 'error_code': 'SECRET_ERROR'}), 403
    except Exception as e:
        app.logger.error(e)
        return jsonify({'error_code': 'GENERIC_ERROR', 'message': e.message}), 500


@mod_api_blueprint.route("/auth/login", methods=['GET'])
def auth0_login():
    """
    This API is responsible for Login through external auth provider
    ---
    tags:
        - auth
    """
    redirect_url = "https://{domain}/login?client={client_id}"\
        .format(domain=app.config['AUTH0_DOMAIN'], client_id=app.config['AUTH0_CLIENT_ID'])
    return redirect(redirect_url)


@mod_api_blueprint.route('/auth/bitstore_upload', methods=['POST'])
def get_s3_signed_url():
    data = request.get_json()
    publisher = data.get('publisher', None)
    package = data.get('package', None)
    path = data.get('path', None)
    if publisher is None or package is None:
        return jsonify({'message': 'publisher or package can not be empty',
                        'error_code': 'INVALID_INPUT'}), 400
    metadata = MetaDataS3(publisher=publisher, package=package)
    url = metadata.generate_pre_signed_put_obj_url(path)
    return jsonify({'key': url}), 200
