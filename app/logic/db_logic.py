# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import os

from flask_marshmallow import Marshmallow
from marshmallow import pre_load, pre_dump
from marshmallow_enum import EnumField

from app.bitstore import BitStore
from app.database import db
import app.models as models
from app.utils import InvalidUsage

ma = Marshmallow()

class LogicBase(object):

    schema = None

    @classmethod
    def serialize(cls, sqla_instance):
        if sqla_instance is None:
            return None
        serialized = cls.schema().dump(sqla_instance).data
        return serialized

    @classmethod
    def deserialize(cls, dict_object):
        deserialized = cls.schema().load(dict_object, session=db.session).data
        return deserialized


#####################################################
# Packages

class PackageSchema(ma.ModelSchema):
    class Meta:
        model = models.Package

    status = EnumField(models.PackageStateEnum)


class PackageTagSchema(ma.ModelSchema):
    class Meta:
        model = models.PackageTag


class PackageMetadataSchema(ma.Schema):
    class Meta:
        fields = ('id', 'name', 'publisher', 'readme', 'descriptor')

    publisher = ma.Method('get_publisher_name')
    readme = ma.Method('get_readme')
    descriptor = ma.Method('get_descriptor')

    def get_publisher_name(self, data):
        return data.publisher.name

    def get_readme(self, data):
        version = filter(lambda t: t.tag == 'latest', data.tags)[0]
        return version.readme or ''

    def get_descriptor(self, data):
        version = filter(lambda t: t.tag == 'latest', data.tags)[0]
        return version.descriptor

class Package(LogicBase):

    schema = PackageSchema

    @classmethod
    def get(cls, publisher, package):
        pkg = models.Package.get_by_publisher(publisher, package)
        return cls.serialize(pkg)

#####################################################
# Profiles - Publishers and Users

class PublisherSchema(ma.ModelSchema):
    class Meta:
        model = models.Publisher
        dateformat = ("%B %Y")

    contact = ma.Method('add_public_contact')
    joined = ma.DateTime(attribute = 'created_at')

    def add_public_contact(self, data):
        if data.contact_public:
            contact = dict(phone=data.phone,
                           email=data.email,
                           country=data.country)
            return contact


class UserSchema(ma.ModelSchema):
    class Meta:
        model = models.User


class UserInfoSchema(ma.Schema):
    class Meta:
        fields = ('email', 'login', 'name')

    @pre_load
    def load_user(self, data):
        email = data.get('email')
        emails = data.get('emails')

        if email:
            return data

        if not emails or not len(emails):
            raise InvalidUsage('Email Not Found', 404)

        for email in emails:
            if email.get('primary') == 'true':
                data['email'] = email.get('email')
                return data


class PublisherUserSchema(ma.ModelSchema):
    class Meta:
        model = models.PublisherUser

    role = EnumField(models.UserRoleEnum)


class Publisher(LogicBase):

    schema = PublisherSchema

    @classmethod
    def get(cls, publisher):
        pub = models.Publisher.get_by_name(publisher)
        return cls.serialize(pub)

    @classmethod
    def create(cls, metadata):
        pub = cls.deserialize(metadata)
        db.session.add(pub)
        db.session.commit()
        return pub

class User(LogicBase):

    schema = UserSchema

    @classmethod
    def get(cls, usr_id):
        usr = models.User.query.get(usr_id)
        return cls.serialize(usr)

    @classmethod
    def create(cls, metadata):
        usr = cls.deserialize(metadata)
        db.session.add(usr)
        db.session.commit()
        return usr


## Logic
#####################

def find_or_create_user(user_info):
    """
    This method populates db when user sign up or login through external auth system
    :param user_info: User data from external auth system
    :param oauth_source: From which oauth source the user coming from e.g. github
    :return: User data from Database
    """
    user = models.User.query.filter_by(name=user_info['login']).one_or_none()
    if user:
        return user

    if user_info.get('name'):
        user_info['full_name'] = user_info.pop('name')
    if user_info.get('login'):
        user_info['name'] = user_info.pop('login')

    user = User.create(user_info)
    # create publisher and accociate with user 
    pub_info = {
        'name': user.name,
        'users': [{'role': 'owner', 'user_id': user.id}]
    }
    Publisher.create(pub_info)

    return user

def get_user_by_id(user_id):
    return User.get(user_id)

def get_publisher(publisher):
    return Publisher.get(publisher)


def create_or_update_package_tag(publisher_name, package_name, tag):
    package = models.Package.query.join(models.Publisher)\
        .filter(models.Publisher.name == publisher_name,
                models.Package.name == package_name).one()

    data_latest = models.PackageTag.query.join(models.Package)\
        .filter(models.Package.id==package.id,
                models.PackageTag.tag=='latest').one()

    tag_instance = models.PackageTag.query.join(models.Package) \
        .filter(models.Package.id==package.id,
                models.PackageTag.tag == tag).first()

    update_props = ['descriptor', 'readme', 'package_id']
    if tag_instance is None:
        tag_instance = models.PackageTag()

    for update_prop in update_props:
        setattr(tag_instance, update_prop, getattr(data_latest, update_prop))
    tag_instance.tag = tag

    db.session.add(tag_instance)
    db.session.commit()
    return True

def create_or_update_package(name, publisher_name, **kwargs):
    """
    This method creates data package or updates data package attributes
    :param name: package name
    :param publisher_name: publisher name
    :param kwargs: package attribute names
    """
    pub_id = models.Publisher.query.filter_by(name=publisher_name).one().id
    instance = models.Package.get_by_publisher(publisher_name, name)

    if instance is None:
        instance = models.Package(name=name)
        instance.publisher_id = pub_id
        tag_instance = models.PackageTag()
        instance.tags.append(tag_instance)
    else:
        tag_instance = models.PackageTag.query.join(models.Package) \
            .filter(models.Package.id == instance.id,
                    models.PackageTag.tag == 'latest').one()
    for key, value in kwargs.items():
        if key not in ['descriptor', 'readme']:
            setattr(instance, key, value)
        else:
            setattr(tag_instance, key, value)
    db.session.add(instance)
    db.session.commit()

def change_package_status(publisher_name, package_name, status=models.PackageStateEnum.active):
    """
    This method changes status of the data package. This method used
    for soft delete the data package
    """
    pkg = models.Package.get_by_publisher(publisher_name, package_name)
    pkg.status = status
    db.session.add(pkg)
    db.session.commit()
    return True

def delete_data_package(publisher_name, package_name):
    pkg = models.Package.get_by_publisher(publisher_name, package_name)
    models.Package.query.filter(models.Package.id == pkg.id).delete()
    db.session.commit()
    return True

def package_exists(publisher_name, package_name):
    instance = models.Package.get_by_publisher(publisher_name, package_name)
    return instance is not None

def get_metadata_for_package(publisher, package):
    '''
    Returns metadata for given package owned by publisher
    '''
    data = models.Package.get_by_publisher(publisher, package)
    if not data:
        return None
    metadata_schema = PackageMetadataSchema()
    metadata = metadata_schema.dump(data).data
    return metadata
