# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import os
from app.database import db
from app.profile.models import User, Publisher, PublisherUser, UserRoleEnum

def find_or_create_user(user_info, oauth_source='github'):
    """
    This method populates db when user sign up or login through external auth system
    :param user_info: User data from external auth system
    :param oauth_source: From which oauth source the user coming from e.g. github
    :return: User data from Database
    """
    user = User.query.filter_by(name=user_info['login']).one_or_none()
    if user is None:
        user = User()
        user.email = user_info.get('email', None)
        user.secret = os.urandom(24).encode('hex')
        user.name = user_info['login']
        user.full_name = user_info.get('name', None)
        user.oauth_source = oauth_source

        publisher = Publisher(name=user.name)
        association = PublisherUser(role=UserRoleEnum.owner)
        association.publisher = publisher
        user.publishers.append(association)

        db.session.add(user)
        db.session.commit()
    return user
