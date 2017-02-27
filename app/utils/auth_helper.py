# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

from app.utils import handle_error
from app.auth.models import JWT
from app.package.models import Package
from app.profile.models import Publisher
from app.auth.authorization import is_allowed as ia


def get_user_from_jwt(req, api_key):
    jwt_helper = JWT(api_key)

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


def get_status(action, publisher, package=None, user_id=None):
    entity_str, action_str = action.split("::")

    if entity_str == 'Package':
        publisher_name, package_name = publisher, package
        instance = Package.get_package(publisher_name, package_name)

    elif entity_str == 'Publisher':
        publisher_name = publisher
        instance = Publisher.query.filter_by(name=publisher_name).one()
    else:
        return handle_error("INVALID_ENTITY", "{e} is not a valid one".format(e=entity_str), 401)

    return ia(user_id, instance, action)

