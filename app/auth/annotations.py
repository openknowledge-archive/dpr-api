# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from functools import wraps

from flask import current_app as app
from flask import request, _request_ctx_stack

from app.utils import InvalidUsage
from app.auth.models import JWT
from app.auth.authorization import is_authorize
from app.logic import db_logic
from app.package.models import Package
from app.profile.models import Publisher


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        status, data = get_user_from_jwt(request, app.config['JWT_SEED'])
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
            jwt_status, user_info = get_user_from_jwt(request, app.config['JWT_SEED'])
            if jwt_status:
                user_id = user_info['user']
            status = check_is_authorized(action, kwargs['publisher'], kwargs['package'], user_id)
            if not status:
                raise InvalidUsage("The operation is not allowed", 403)
            return f(*args, **kwargs)
        return wrapped
    return wrapper


def get_user_from_jwt(req, api_key):
    jwt_helper = JWT(api_key)

    token = req.headers.get('Authorization', None)
    if token is None:
        token = req.headers.get('Auth-Token', None)
    if token is None:
        token = req.values.get('jwt')

    if not token:
        raise InvalidUsage('Authorization header is expected', 401)
    try:
        return True, jwt_helper.decode(token)
    except Exception as e:
        raise InvalidUsage(e.message, 400)


def check_is_authorized(action, publisher, package=None, user_id=None):
    entity_str, action_str = action.split("::")

    if entity_str == 'Package':
        publisher_name, package_name = publisher, package
        instance = db_logic.get_package(publisher_name, package_name)

    elif entity_str == 'Publisher':
        publisher_name = publisher
        instance = Publisher.query.filter_by(name=publisher_name).one()
    else:
        raise InvalidUsage("{e} is not a valid one".format(e=entity_str), 401)

    return is_authorize(user_id, instance, action)
