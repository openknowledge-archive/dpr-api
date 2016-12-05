# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

from functools import wraps
from flask import request

from app.utils.auth import get_user_from_jwt, handle_error
from app.mod_api.models import User, MetaDataDB, Publisher, PublisherUser


roles = {
    "Package": {
        "Owner": ["Package::Read", "Package::Create", "Package::Delete",
                  "Package::Undelete", "Package::Purge", "Package::Update",
                  "Package::Tag"],
        "Editor": ["Package::Read", "Package::Create", "Package::Delete",
                   "Package::Undelete", "Package::Update", "Package::Tag"],
        "Viewer": ["Package::Read"]
    },
    "Publisher": {
        "Owner": ["Publisher::AddMember", "Publisher::RemoveMember",
                  "Publisher::Create", "Publisher::Read", "Publisher::Delete",
                  "Publisher::Update", "Publisher::ViewMemberList"],
        "Editor": ["Publisher::ViewMemberList", "Publisher::AddMember",
                   "Publisher::RemoveMember", "Publisher::Read"],
        "Viewer": ["Publisher::Read"]
    },
    "System": {
        "LoggedIn": ["Package::Create", "Publisher::Create"],
        "Anonymous": ["Package::Read"],
        "Sysadmin": ["Package::Read", "Package::Create", "Package::Delete",
                     "Package::Undelete", "Package::Purge", "Package::Update",
                     "Package::Tag", "Publisher::AddMember", "Publisher::RemoveMember",
                     "Publisher::Create", "Publisher::Read", "Publisher::Delete",
                     "Publisher::Update", "Publisher::ViewMemberList"]
    }
}


def is_allowed(action):
    def wrapper(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            entity_str, action_str = action.split("::")
            user_id, instance = None, None
            jwt_status, user_info = get_user_from_jwt(request)
            if jwt_status:
                user_id = user_info['user']

            if entity_str == 'Package':
                publisher_name, package_name = kwargs['publisher'], kwargs['package']
                instance = MetaDataDB.get_package(publisher_name, package_name)

            elif entity_str == 'Publisher':
                publisher_name = kwargs['publisher']
                instance = Publisher.query.filter_by(name=publisher_name).one()
            else:
                return handle_error("INVALID_ENTITY", "{e} is not a valid one".format(e=entity_str), 401)
            if instance is None:
                return handle_error("INVALID_INPUT", "Could not find publisher or package", 404)
            status = is_role_allowed(user_id, instance, action)
            if not status:
                return handle_error("NOT_ALLOWED", "The operation is not allowed", 403)
            return f(*args, **kwargs)
        return wrapped
    return wrapper


def is_role_allowed(user_id, entity, action):
    local_roles = get_roles(user_id, entity)
    return action in local_roles


def get_roles(user_id, entity):
    local_roles = []
    if user_id is None:
        if entity.private is False:
            local_roles.extend(roles['System']['Anonymous'])
    else:
        user = User.query.get(user_id)
        if user.sysadmin is True:
            local_roles.extend(roles['System']['Sysadmin'])
        else:
            if isinstance(entity, Publisher):
                local_roles.extend(get_publisher_roles(user_id=user_id, entity=entity))
            if isinstance(entity, MetaDataDB):
                local_roles.extend(get_package_roles(user_id=user_id, entity=entity))
    return local_roles


def get_publisher_roles(user_id, entity):
    role_parent = 'Publisher'
    publisher_roles = []
    try:
        user_role = PublisherUser.query.join(User).join(Publisher)\
            .filter(User.id == user_id, Publisher.name == entity.name).one()
        if user_role.role == 'OWNER':
            publisher_roles.extend(roles[role_parent]['Owner'])
        elif user_role.role == 'MEMBER':
            publisher_roles.extend(roles[role_parent]['Editor'])
    except:
        publisher_roles.extend(roles['System']['LoggedIn'])
        if entity.private is not True:
            publisher_roles.extend(roles[role_parent]['Viewer'])
    return publisher_roles


def get_package_roles(user_id, entity):
    role_parent = 'Package'
    package_roles = []
    try:
        user_role = PublisherUser.query.join(User).join(Publisher)\
            .filter(User.id == user_id, Publisher.name == entity.publisher.name)\
            .one()
        if user_role.role == 'OWNER':
            package_roles.extend(roles[role_parent]['Owner'])
        elif user_role.role == 'MEMBER':
            package_roles.extend(roles[role_parent]['Editor'])
    except:
        package_roles.extend(roles['System']['LoggedIn'])
        if entity.private is not True:
            package_roles.extend(roles[role_parent]['Viewer'])
    return package_roles
