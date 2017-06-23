# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from flask import Blueprint, jsonify, session, request, g, make_response, render_template
from flask import current_app as app
import app.logic as logic
import app.auth.jwt as jwt
from app.auth.annotations import get_user_from_jwt

auth_blueprint = Blueprint('auth', __name__, url_prefix='/api/auth')
bitstore_blueprint = Blueprint('bitstore', __name__, url_prefix='/api/datastore')


@auth_blueprint.route("/callback")
def callback_handling():
    """
    Callback API for redirecting to external auth provider.
    ---
    tags:
        - auth
    response:
        500:
            description: Internal Server Error
        404:
            description: Email Not Found For User
        400:
            description: Access Denied
        200:
            description: Updated DB with user
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
    user_info = logic.get_authorized_user_info()
    user = logic.User.find_or_create(user_info)
    jwt_helper = jwt.JWT(app.config['JWT_SEED'], user.id)
    session.pop('github_token', None)
    g.current_user = user

    resp = make_response(render_template("dashboard.html",
                         title='Dashboard'), 200)
    resp.set_cookie('jwt', jwt_helper.encode())
    return resp

@auth_blueprint.route("/token", methods=['POST'])
def get_jwt():
    """
    Returns JWT token
    ---
    tags:
        - auth
    parameters:
        - in: body
          name: email
          type: string
          required: false
          description: user email
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
    data = request.get_json()
    token = logic.get_jwt_token(
            secret=data.get('secret', None),
            username=data.get('username', None),
            email=data.get('email', None)
            )
    return jsonify({'token': token}), 200


@auth_blueprint.route("/login", methods=['GET'])
def auth0_login():
    """
    Login through external auth provider
    ---
    tags:
        - auth
    """
    callback_url = request.scheme + '://' + request.headers['Host'] + '/api/auth/callback'
    return app.config['github'].authorize(callback=callback_url)


@bitstore_blueprint.route('/authorize', methods=['POST'])
def authorize_upload():
    """
    Generates signed URLs for multiple files for posting data to S3
    ---
    tags:
        - package
    parameters:
        - in: body
          name: data
          type: map
          required: true
          description: publisher name, package name and file details
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
    user_id = None
    jwt_status, user_info = get_user_from_jwt(request, app.config['JWT_SEED'])
    if jwt_status:
        user_id = user_info['user']

    data = request.get_json()
    payload = logic.generate_signed_url(user_id, data)
    return jsonify(payload), 200
