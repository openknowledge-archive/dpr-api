import json
from flask import Blueprint, request, jsonify, _request_ctx_stack, render_template
from flask import current_app as app
from flask import redirect
from app.database import db, s3
from app.mod_api.models import MetaDataS3, User, MetaDataDB
from app.utils.auth import requires_auth
from app.utils.auth0_helper import get_user_info_with_code, update_user_secret, get_user
from app.utils.jwt_utilities import JWTHelper

mod_api = Blueprint('api', __name__, url_prefix='/api')


@mod_api.route("/package/<publisher>/<package>", methods=["PUT"])
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
        user = _request_ctx_stack.top.current_user
        user_id = user['user']
        user = User.query.filter_by(user_id=user_id).first()
        if user is not None:
            if user.user_name == publisher:
                metadata = MetaDataS3(publisher=publisher, package=package, body=request.data)
                metadata.save()
                return jsonify({"status": "OK"}), 200
            return jsonify({"status": "KO", "message": 'user name and publisher not matched'}), 400
        return jsonify({"status": "KO", "message": 'user not found'}), 400
    except Exception as e:
        app.logger.error(e)
        return jsonify({'status': 'KO', 'message': e.message}), 500


@mod_api.route("/package/<publisher>/<package>", methods=["GET"])
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
    user_info = get_user_info_with_code(code)
    user_id = user_info['user_id']
    if 'user_metadata' in user_info and 'secret' not in user_info['user_metadata']:
        update_user_secret(user_id)
    else:
        update_user_secret(user_id)

    user_info = get_user(user_id)
    jwt_helper = JWTHelper(app.config['API_KEY'], user_id)

    user = User.query.filter_by(user_id=user_id).first()
    if user is None:
        user = User()
        user.email = user_info['email']
        user.secret = user_info['user_metadata']['secret']
        user.user_id = user_info['user_id']
        user.user_name = user_info['username']
        db.session.add(user)
        db.session.commit()
    user = User.query.filter_by(user_id=user_id).first()
    ## For now dashboard is rendered directly from callbacl, this needs to be changed
    return render_template("dashboard.html", user=user.serialize['name'])
    # return jsonify({'status': 'OK', 'token': jwt_helper.encode(), 'user': user.serialize}), 200


@mod_api.route("/auth/token", methods=['POST'])
def get_jwt():
    """
    This API is responsible for Login
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
    """
    data = request.get_json()
    user_name = data.get('username', None)
    email = data.get('email', None)
    secret = data.get('secret', None)
    verify = False
    user_id = None
    if user_name is None and email is None:
        return jsonify({'message': 'User name or email both can not be empty'}), 400
    elif user_name is not None:
        user = User.query.filter_by(user_name=user_name).first()
        if user is None:
            return jsonify({'status': 'KO', 'message': 'user does not exists'}), 400
        if secret == user.secret:
            verify = True
            user_id = user.user_id
    elif email is not None:
        user = User.query.filter_by(email=email).first()
        if user is None:
            return jsonify({'status': 'KO', 'message': 'user does not exists'}), 400
        if secret == user.secret:
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
    redirect_url = "https://{domain}/login?client={client_id}"\
        .format(domain=app.config['AUTH0_DOMAIN'], client_id=app.config['AUTH0_CLIENT_ID'])
    return redirect(redirect_url)


@mod_api.route('/s3_url/<publisher>/<package>', methods=['GET'])
def get_s3_signed_url(publisher, package):
    """Look at http://stackoverflow.com/questions/34583869/descriptions-of-boto3-clientmethods"""
    metadata = MetaDataS3(publisher=publisher, package=package)
    return jsonify({'key': metadata.generate_pre_signed_put_obj_url()})
