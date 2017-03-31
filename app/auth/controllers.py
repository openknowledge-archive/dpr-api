# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from flask import Blueprint, request, render_template, \
    jsonify, session, make_response, g
from flask import current_app as app
from app.profile.models import User
from app.auth.models import JWT, FileData
from app.package.models import Package
from app.utils import handle_error
from app.auth.annotations import check_is_authorized, get_user_from_jwt

auth_blueprint = Blueprint('auth', __name__, url_prefix='/api/auth')
bitstore_blueprint = Blueprint('bitstore', __name__, url_prefix='/api/datastore')


@auth_blueprint.route("/callback")
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
        github = app.config['github']
        resp = github.authorized_response()
        if resp is None or resp.get('access_token') is None:
            return handle_error('Access Denied',
                                request.args['error_description'],
                                400)
        session['github_token'] = (resp['access_token'], '')
        user_info = github.get('user')
        user = User().create_or_update_user_from_callback(user_info.data)
        jwt_helper = JWT(app.config['JWT_SEED'], user.id)
        session.pop('github_token', None)
        g.current_user = user
        resp = make_response(render_template("dashboard.html",
                             title='Dashboard'), 200)
        resp.set_cookie('jwt', jwt_helper.encode())
        return resp
    except Exception as e:
        app.logger.error(e)
        return handle_error('GENERIC_ERROR', e.message, 500)


@auth_blueprint.route("/token", methods=['POST'])
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
            user = User.query.filter_by(name=user_name).first()
            if user is None:
                return handle_error('USER_NOT_FOUND',
                                    'user does not exists',
                                    404)
            if secret == user.secret:
                verify = True
                user_id = user.id
        elif email is not None:
            user = User.query.filter_by(email=email).first()
            if user is None:
                return handle_error('USER_NOT_FOUND',
                                    'user does not exists',
                                    404)
            if secret == user.secret:
                verify = True
                user_id = user.id
        if verify:
            return jsonify({'token': JWT(app.config['JWT_SEED'],
                                         user_id).encode()}), 200
        else:
            return handle_error('SECRET_ERROR',
                                'Secret key do not match',
                                403)
    except Exception as e:
        app.logger.error(e)
        return handle_error('GENERIC_ERROR', e.message, 500)


@auth_blueprint.route("/login", methods=['GET'])
def auth0_login():
    """
    This API is responsible for Login through external auth provider
    ---
    tags:
        - auth
    """
    callback_url = request.scheme + '://' + request.headers['Host'] + '/api/auth/callback'
    return app.config['github'].authorize(callback=callback_url)


@bitstore_blueprint.route('/authorize', methods=['POST'])
def authorize_upload():
    """
    This API is responsible for generate signed urls for multiple files
    to post data to S3
    ---
    tags:
        - auth
    parameters:
        - in: body
          name: data
          type: map
          required: true
          description: publisher name and package name, and file details
    responses:
        200:
            description: Success
            schema:
                id: get_signed_url
                properties:
                    filedata:
                        type: map
                        description: Signed url and upload_query
        400:
            description: Unauthorized
        500:
            description: Internal Server Error
    """
    try:
        user_id = None
        jwt_status, user_info = get_user_from_jwt(request, app.config['JWT_SEED'])
        if jwt_status:
            user_id = user_info['user']

        data = request.get_json()
        metadata, filedata = data['metadata'], data['filedata']
        publisher, package_name = metadata['owner'], metadata['name']
        res_payload = {'filedata': {}}

        if Package.is_package_exists(publisher, package_name):
            status = check_is_authorized('Package::Update', publisher, package_name, user_id)
        else:
            status = check_is_authorized('Package::Create', publisher, package_name, user_id)

        if not status:
            return handle_error('UN-AUTHORIZE', 'not authorized to upload data', 400)

        for relative_path in filedata.keys():
            response = FileData(package_name=package_name,
                                publisher=publisher,
                                relative_path=relative_path,
                                props=filedata[relative_path])
            res_payload['filedata'][relative_path] = response.build_file_information()

        return jsonify(res_payload), 200
    except Exception as e:
        app.logger.error(e)
        return handle_error('GENERIC_ERROR', e.message, 500)
