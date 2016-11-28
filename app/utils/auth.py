# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

from functools import wraps
from flask import request, _request_ctx_stack
from flask import current_app as app
from app.mod_api.models import User
from app.utils import handle_error
from app.utils.jwt_utilities import JWTHelper


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        jwt_helper = JWTHelper(app.config['API_KEY'])

        auth = request.headers.get('Authorization', None)

        if not auth:
            return handle_error('authorization_header_missing',
                                'Authorization header is expected', 401)
        parts = auth.split()
        if parts[0].lower() != 'bearer':
            return handle_error('invalid_header',
                                'Authorization header must start with Bearer',
                                401)
        elif len(parts) == 1:
            return handle_error('invalid_header', 'Token not found', 401)
        elif len(parts) > 2:
            return handle_error(
                'invalid_header',
                'Authorization header must\ be Bearer + \s + token',
                401)
        token = parts[1]
        try:
            payload = jwt_helper.decode(token)
        except Exception as e:
            return handle_error('jwt_error', e.message, 400)
        _request_ctx_stack.top.current_user = user = payload
        return f(*args, **kwargs)

    return decorated


def requires_roles(roles):
    def wrapper(f):
        @wraps(f)
        def wrapped(publisher, *args, **kwargs):
            user = _request_ctx_stack.top.current_user
            user_id = user['user']
            user = User.query.filter_by(id=user_id).first()
            if user is None:
                return handle_error(
                    'USER_NOT_FOUND',
                    'user not found',
                    404)
            if User.get_user_role(user_id, publisher) not in roles:
                return handle_error(
                    'unauthorized',
                    'The user is not authorized to do this operation',
                    403)
            return f(publisher, *args, **kwargs)
        return wrapped
    return wrapper
