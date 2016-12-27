# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from flask import Blueprint, request, render_template, \
    jsonify, redirect
from flask import current_app as app
from app.package.models import BitStore, User
from app.auth.models import JWT, Auth0
from app.utils import get_zappa_prefix, get_s3_cdn_prefix, handle_error


auth_blueprint = Blueprint('auth', __name__, url_prefix='/api/auth')


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
        code = request.args.get('code')
        auth0 = Auth0()
        user_info = auth0.get_user_info_with_code(code, request.base_url)

        user = User().create_or_update_user_from_callback(user_info)
        jwt_helper = JWT(app.config['API_KEY'], user.id)

        return render_template("dashboard.html", user=user,
                               title='Dashboard',
                               encoded_token=jwt_helper.encode(),
                               zappa_env=get_zappa_prefix(),
                               s3_cdn=get_s3_cdn_prefix()), 200
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
            return jsonify({'token': JWT(app.config['API_KEY'],
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
    redirect_url = "https://{domain}/login?client={client_id}"\
        .format(domain=app.config['AUTH0_DOMAIN'],
                client_id=app.config['AUTH0_CLIENT_ID'])
    return redirect(redirect_url)


@auth_blueprint.route('/bitstore_upload', methods=['POST'])
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
        md5 = data.get('md5', None)
        if publisher is None or package is None:
            return handle_error('INVALID_INPUT',
                                'publisher or package can not be empty',
                                400)
        if md5 is None:
            return handle_error('INVALID_INPUT',
                                'md5 hash can not be empty',
                                400)
        metadata = BitStore(publisher=publisher, package=package)
        url = metadata.generate_pre_signed_put_obj_url(path, md5)
        return jsonify({'key': url}), 200
    except Exception as e:
        app.logger.error(e)
        return handle_error('GENERIC_ERROR', e.message, 500)
