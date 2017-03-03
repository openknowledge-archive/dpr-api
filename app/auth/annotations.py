# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from functools import wraps

from flask import current_app as app
from flask import request, _request_ctx_stack

from app.utils import handle_error
from app.utils.auth_helper import get_user_from_jwt, check_is_authorized


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        status, data = get_user_from_jwt(request, app.config['API_KEY'])
        if status:
            _request_ctx_stack.top.current_user = data
            return f(*args, **kwargs)
        else:
            return data
    return decorated


def is_allowed(action):
    def wrapper(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            user_id, instance = None, None
            jwt_status, user_info = get_user_from_jwt(request, app.config['API_KEY'])
            if jwt_status:
                user_id = user_info['user']
            status = check_is_authorized(action, kwargs['publisher'], kwargs['package'], user_id)
            if not status:
                return handle_error("NOT_ALLOWED", "The operation is not allowed", 403)
            return f(*args, **kwargs)
        return wrapped
    return wrapper
