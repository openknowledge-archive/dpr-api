# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime
import enum
import os
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from app.database import db


class Publisher(db.Model):
    """
    This class is DB model for storing publisher attributes
    """
    __tablename__ = 'publisher'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    name = db.Column(db.TEXT, unique=True, index=True, nullable=False)
    title = db.Column(db.Text)
    private = db.Column(db.BOOLEAN, default=False)
    description = db.Column(db.Text)
    country = db.Column(db.Text)
    email = db.Column(db.Text)
    phone = db.Column(db.Text)
    contact_public = db.Column(db.BOOLEAN)

    packages = relationship("Package", back_populates="publisher")

    users = relationship("PublisherUser", back_populates="publisher",
                         cascade='save-update, merge, delete, delete-orphan')


class User(db.Model):
    """
    This class is DB model for storing user attributes
    """

    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    email = db.Column(db.TEXT, unique=True, index=True)
    secret = db.Column(db.TEXT)
    name = db.Column(db.TEXT, unique=True, index=True, nullable=False)
    full_name = db.Column(db.TEXT)
    sysadmin = db.Column(db.BOOLEAN, default=False)
    oauth_source = db.Column(db.TEXT, default=None)

    publishers = relationship("PublisherUser", back_populates="user",
                              cascade='save-update, merge, delete, delete-orphan')

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'full_name': self.full_name,
            'email': self.email,
            'name': self.name,
            'secret': self.secret
        }

    @staticmethod
    def create_or_update_user_from_callback(user_info, oauth_source='github'):
        """
        This method populates db when user sign up or login through external auth system
        :param user_info: User data from external auth system
        :param oauth_source: From which oauth source the user coming from e.g. github
        :return: User data from Database
        """
        user = User.query.filter_by(name=user_info['login']).first()
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


class UserRoleEnum(enum.Enum):
    owner = "OWNER"
    member = "MEMBER"


class PublisherUser(db.Model):
    """
    This class is association object between user and publisher
    as they have many to many relationship
    """
    __tablename__ = 'publisher_user'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    user_id = db.Column(db.Integer, ForeignKey('user.id'), primary_key=True)
    publisher_id = db.Column(db.Integer, ForeignKey('publisher.id'), primary_key=True)

    role = db.Column(db.Enum(UserRoleEnum, native_enum=False), nullable=False)
    """role can only OWNER or MEMBER"""

    publisher = relationship("Publisher", back_populates="users")
    user = relationship("User", back_populates="publishers")
