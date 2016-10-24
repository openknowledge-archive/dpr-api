import json
from flask import Blueprint, request, jsonify
from flask import current_app as app
from flask import redirect

from app.mod_api.models import MetaDataS3, User
from app.utils.auth import requires_auth
from app.utils.auth0_helper import get_user_info
from app.utils.jwt_utilities import JWTHelper

mod_api = Blueprint('api', __name__, url_prefix='/api')


@mod_api.route("/<publisher>/<package>", methods=["PUT"])
@requires_auth
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
        app.logger.error(e)
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
        metadata = MetaDataS3(publisher=publisher, package=package)
        return jsonify({"data": json.loads(metadata.get_metadata_body()), "status": "OK"}), 200
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


@mod_api.route("/callback")
def callback_handling():
    """
    This ia callback api when we redirect the api to Auth0 or any external
    Auth provider.
    ---
    tags:
        - auth
        - auth0
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
    code = request.args.get('code')
    user_info = get_user_info(code)
    user_id = user_info['user_id']

    # TODO SYNC with local DB

    jwt_helper = JWTHelper(app.config['API_KEY'], user_id)
    user = User()
    user.email = user_info['email']
    user.nickname = user_info['nickname']
    user.picture = user_info['picture']
    user.name = user_info['name']
    return jsonify({'status': 'OK', 'token': jwt_helper.encode(), 'user': user.json}), 200


@mod_api.route("/login", methods=['POST'])
def login():
    """
    This API is responsible for Login
    ---
    tags:
        - auth
    parameters:
        - in: body
          name: email
          type: string
          required: true
          description: user email id
        - in: body
          name: username
          type: string
          required: true
          description: user name
        - in: body
          name: password
          type: string
          required: true
          description: user password
    """
    data = request.get_json()
    user_name = data.get('username', None)
    email = data.get('email', None)
    password = data.get('password', None)
    verify = False
    user_id = None
    if user_name is None and email is None:
        return jsonify({'message': 'User name or email both can not be empty'}), 400
    elif user_name is not None:
        user = User.query.filter_by(user_id=user_name).first()
        if user is None:
            return jsonify({'status': 'KO', 'message': 'user does not exists'}), 400
        if password == user.password:
            verify = True
            user_id = user.user_id
    elif email is not None:
        user = User.query.filter_by(user_id=email).first()
        if user is None:
            return jsonify({'status': 'KO', 'message': 'user does not exists'}), 400
        if password == user.password:
            verify = True
            user_id = user.user_id
    if verify:
        return jsonify({'status': 'OK', 'token': JWTHelper(app.config['API_KEY'], user_id).encode()})


@mod_api.route("/login", methods=['GET'])
def auth0_login():
    """
    This API is responsible for Login through external auth provider
    ---
    tags:
        - auth
        - auth0
    """
    return redirect(app.config['AUTH0_LOGIN_PAGE'])
