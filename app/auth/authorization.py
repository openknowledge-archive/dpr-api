# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

from app.package.models import User, MetaDataDB, Publisher, \
    PublisherUser, UserRoleEnum


roles_action_mappings = {
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
        "Anonymous": ["Package::Read", "Publisher::Read"],
        "Sysadmin": ["Package::Read", "Package::Create", "Package::Delete",
                     "Package::Undelete", "Package::Purge", "Package::Update",
                     "Package::Tag", "Publisher::AddMember", "Publisher::RemoveMember",
                     "Publisher::Create", "Publisher::Read", "Publisher::Delete",
                     "Publisher::Update", "Publisher::ViewMemberList"]
    }
}


def is_allowed(user_id, entity, action):
    actions = get_user_actions(user_id, entity)
    return action in actions


def get_user_actions(user_id, entity):
    local_roles = []
    user = None
    if user_id is not None:
        user = User.query.get(user_id)
    if user is None:
        if entity is not None and entity.private is False:
            local_roles.extend(roles_action_mappings['System']['Anonymous'])
    else:
        if user.sysadmin is True:
            local_roles.extend(roles_action_mappings['System']['Sysadmin'])
        else:
            if isinstance(entity, Publisher):
                local_roles.extend(get_publisher_roles(user_id=user_id, entity=entity))
            if isinstance(entity, MetaDataDB):
                local_roles.extend(get_package_roles(user_id=user_id, entity=entity))
            elif entity is None:
                local_roles.extend(roles_action_mappings['System']['LoggedIn'])
    return local_roles


def get_publisher_roles(user_id, entity):
    role_parent = 'Publisher'
    publisher_roles = []
    try:
        user_role = PublisherUser.query.join(User).join(Publisher)\
            .filter(User.id == user_id, Publisher.name == entity.name).one()
        if user_role.role == UserRoleEnum.owner:
            publisher_roles.extend(roles_action_mappings[role_parent]['Owner'])
        elif user_role.role == UserRoleEnum.member:
            publisher_roles.extend(roles_action_mappings[role_parent]['Editor'])
    except:
        publisher_roles.extend(roles_action_mappings['System']['LoggedIn'])
        if entity.private is not True:
            publisher_roles.extend(roles_action_mappings[role_parent]['Viewer'])
    return publisher_roles


def get_package_roles(user_id, entity):
    role_parent = 'Package'
    package_roles = []
    try:
        user_role = PublisherUser.query.join(User).join(Publisher)\
            .filter(User.id == user_id, Publisher.name == entity.publisher.name)\
            .one()
        if user_role.role == UserRoleEnum.owner:
            package_roles.extend(roles_action_mappings[role_parent]['Owner'])
        elif user_role.role == UserRoleEnum.member:
            package_roles.extend(roles_action_mappings[role_parent]['Editor'])
    except:
        package_roles.extend(roles_action_mappings['System']['LoggedIn'])
        if entity.private is not True:
            package_roles.extend(roles_action_mappings[role_parent]['Viewer'])
    return package_roles
