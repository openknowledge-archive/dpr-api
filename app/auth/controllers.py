# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from flask import Blueprint, request, render_template, \
    jsonify, session, make_response, g
from flask import current_app as app
from sqlalchemy.orm.exc import NoResultFound

from app.profile.models import User
from app.auth.models import JWT, FileData
from app.package.models import Package
from app.utils import InvalidUsage
from app.auth.annotations import check_is_authorized, get_user_from_jwt

auth_blueprint = Blueprint('auth', __name__, url_prefix='/api/auth')
bitstore_blueprint = Blueprint('bitstore', __name__, url_prefix='/api/datastore')


@auth_blueprint.route("/callback")
def callback_handling():
    """
    Callback API for redirecting to Auth0 or any external auth provider.
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
    github = app.config['github']
    resp = github.authorized_response()
    if resp is None or resp.get('access_token') is None:
        raise InvalidUsage('Access Denied', 400)
    session['github_token'] = (resp['access_token'], '')
    user_info = github.get('user')
    user_info = user_info.data
    # in case user Email is not public
    if not user_info.get('email'):
        emails = github.get('user/emails').data
        if not len(emails):
            raise InvalidUsage('Email Not Found', 404)
        for email in emails:
            if email.get('primary'):
                user_info['email'] = email.get('email')
    user = User().create_or_update_user_from_callback(user_info)
    jwt_helper = JWT(app.config['JWT_SEED'], user.id)
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
    user_name = data.get('username', None)
    email = data.get('email', None)
    secret = data.get('secret', None)
    verify = False
    user_id = None
    if user_name is None and email is None:
        raise InvalidUsage('User name or email both can not be empty', 400)

    if secret is None:
        raise InvalidUsage('Secret can not be empty', 400)
    elif user_name is not None:
        try:
            user = User.query.filter_by(name=user_name).one()
        except NoResultFound as e:
            app.logger.error(e)
            raise InvalidUsage('user does not exists', 404)
        if secret == user.secret:
            verify = True
            user_id = user.id
    elif email is not None:
        try:
            user = User.query.filter_by(email=email).one()
        except NoResultFound as e:
            app.logger.error(e)
            raise InvalidUsage('user does not exists', 404)
        if secret == user.secret:
            verify = True
            user_id = user.id
    if verify:
        return jsonify({'token': JWT(app.config['JWT_SEED'],
                                     user_id).encode()}), 200
    else:
        raise InvalidUsage('Secret key do not match', 403)


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
    metadata, filedata = data['metadata'], data['filedata']
    publisher, package_name = metadata['owner'], metadata['name']
    res_payload = {'filedata': {}}

    if Package.is_package_exists(publisher, package_name):
        status = check_is_authorized('Package::Update', publisher, package_name, user_id)
    else:
        status = check_is_authorized('Package::Create', publisher, package_name, user_id)

    if not status:
        raise InvalidUsage('Not authorized to upload data', 400)

    for relative_path in filedata.keys():
        response = FileData(package_name=package_name,
                            publisher=publisher,
                            relative_path=relative_path,
                            props=filedata[relative_path])
        res_payload['filedata'][relative_path] = response.build_file_information()

    return jsonify(res_payload), 200
