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
    schema = PackageMetadataSchema

    @classmethod
    def get(cls, publisher, package):
        data = models.Package.get_by_publisher(publisher, package)
        return cls.serialize(data)

    @classmethod
    def exists(cls, publisher, package):
        instance = models.Package.get_by_publisher(publisher, package)
        return instance is not None

    @classmethod
    def delete(cls, publisher, package):
        pkg = models.Package.get_by_publisher(publisher, package)
        # TODO: should be able to db.session.delete(pkg) but deletes publishers!
        models.Package.query.filter(models.Package.id == pkg.id).delete()
        db.session.commit()
        return True

    @classmethod
    def create_or_update_tag(cls, publisher, package, tag):
        package = models.Package.get_by_publisher(publisher, package)

        data_latest = models.PackageTag.query.join(models.Package)\
            .filter(models.Package.id == package.id,
                    models.PackageTag.tag == 'latest').one()

        tag_instance = models.PackageTag.query.join(models.Package) \
            .filter(models.Package.id == package.id,
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

    @classmethod
    def create_or_update(cls, name, publisher_name, **kwargs):
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

    @classmethod
    def change_status(cls, publisher_name,
                            package_name, status=models.PackageStateEnum.active):
        pkg = models.Package.get_by_publisher(publisher_name, package_name)
        pkg.status = status
        db.session.add(pkg)
        db.session.commit()
        return True


class PackageTag(LogicBase):
    schema = PackageTagSchema

    @classmethod
    def get(cls, package_id, tag):
        tag = models.PackageTag.get_by_tag(package_id, tag)
        return cls.serialize(tag)

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

    @classmethod
    def find_or_create(cls, user_info):
        """
        This method populates db when user sign up or login through external auth system
        :param user_info: User data from external auth system
        :param oauth_source: From which oauth source the user coming from e.g. github
        :return: User data from Database
        """
        user = models.User.get_by_name(user_info['login'])
        if user:
            return user

        # convert github info to our local user info
        ourinfo = {
            'name': user_info['login'],
            'full_name': user_info.get('name'),
            'email': user_info.get('email')
        }
        user = models.User(**ourinfo)
        # create publisher for this user
        publisher = models.Publisher(name=user.name)
        association = models.PublisherUser(role=models.UserRoleEnum.owner, publisher=publisher, user=user)
        # user.publishers.append(association)
        db.session.add(user)
        db.session.commit()
        return user


## Logic
#####################

def find_or_create_user(user_info):
    return User.find_or_create(user_info)

def get_user_by_id(user_id):
    return User.get(user_id)

def get_publisher(publisher):
    return Publisher.get(publisher)

def create_or_update_package_tag(publisher_name, package_name, tag):
    return Package.create_or_update_tag(publisher_name, package_name, tag)

def create_or_update_package(package_name, publisher_name, **kwargs):

    Package.create_or_update(package_name, publisher_name, **kwargs)

def change_package_status(publisher_name, package_name, status=models.PackageStateEnum.active):
    return Package.change_status(publisher_name, package_name, status)

def delete_data_package(publisher, package):
    return Package.delete(publisher, package)

def package_exists(publisher, package):
    return Package.exists(publisher, package)

def get_metadata_for_package(publisher, package):
    return Package.get(publisher, package)
