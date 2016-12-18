# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

from app.utils import handle_error
from app.utils.jwt_utilities import JWTHelper


def get_user_from_jwt(req, api_key):
    jwt_helper = JWTHelper(api_key)

    auth = req.headers.get('Authorization', None)

    if not auth:
        return False, handle_error('authorization_header_missing',
                                   'Authorization header is expected', 401)
    parts = auth.split()
    if parts[0].lower() != 'bearer':
        return False, handle_error('invalid_header',
                                   'Authorization header must start with Bearer',
                                   401)
    elif len(parts) == 1:
        return False, handle_error('invalid_header', 'Token not found', 401)
    elif len(parts) > 2:
        return False, handle_error(
            'invalid_header',
            'Authorization header must\ be Bearer + \s + token',
            401)
    token = parts[1]
    try:
        return True, jwt_helper.decode(token)
    except Exception as e:
        return False, handle_error('jwt_error', e.message, 400)
