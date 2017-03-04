# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

from app.utils import handle_error
from app.auth.models import JWT
from app.package.models import Package
from app.profile.models import Publisher
from app.auth.authorization import is_authorize


def get_user_from_jwt(req, api_key):
    jwt_helper = JWT(api_key)

    token = req.headers.get('Authorization', None)
    if token is None:
        token = req.headers.get('Auth-Token', None)
    if token is None:
        token = req.values.get('jwt')

    if not token:
        return False, handle_error('authorization_header_missing',
                                   'Authorization header is expected', 401)
    try:
        return True, jwt_helper.decode(token)
    except Exception as e:
        return False, handle_error('jwt_error', e.message, 400)


def check_is_authorized(action, publisher, package=None, user_id=None):
    entity_str, action_str = action.split("::")

    if entity_str == 'Package':
        publisher_name, package_name = publisher, package
        instance = Package.get_package(publisher_name, package_name)

    elif entity_str == 'Publisher':
        publisher_name = publisher
        instance = Publisher.query.filter_by(name=publisher_name).one()
    else:
        return handle_error("INVALID_ENTITY", "{e} is not a valid one".format(e=entity_str), 401)

    return is_authorize(user_id, instance, action)
