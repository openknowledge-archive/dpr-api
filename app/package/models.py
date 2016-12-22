# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import json
import os
import datetime

import enum
from sqlalchemy import ForeignKey
from sqlalchemy import UniqueConstraint
from flask import current_app as app
from sqlalchemy.orm import relationship

from app.database import db


class BitStore(object):
    """
    This model responsible for interaction with S3
    """
    prefix = 'metadata'

    def __init__(self, publisher, package, version='latest', body=None):
        self.publisher = publisher
        self.package = package
        self.version = version
        self.body = body

    def validate(self):
        data = json.loads(self.body)
        if 'name' not in data:
            return False
        if data['name'] == '':
            return False
        return True

    def save_metadata(self, acl='public-read'):
        """
        This method put metadata object to S3
        """
        bucket_name = app.config['S3_BUCKET_NAME']
        s3_client = app.config['S3']
        key = self.build_s3_key('datapackage.json')
        s3_client.put_object(Bucket=bucket_name, Key=key,
                             Body=self.body, ACL=acl)

    def get_metadata_body(self):
        """
        This method retrieve datapackage.json from s3 for specific
        publisher and package
        :return: The String value of the datapackage.json or None of not found
        """
        key = self.build_s3_key('datapackage.json')
        return self.get_s3_object(key)

    def get_s3_object(self, key):
        """
        This method retrieve any object from s3 for a given key.
        :param key: Object key to be retrieved
        :return: The String value of the object or None of not found
        """
        try:
            bucket_name = app.config['S3_BUCKET_NAME']
            s3_client = app.config['S3']
            response = s3_client.get_object(Bucket=bucket_name, Key=key)
            return response['Body'].read()
        except Exception:
            return None

    def get_readme_object_key(self):
        """
        This method search for any readme object is present for the
        generated prefix by:
        >>> BitStore.build_s3_prefix()
        :return: Value of the readme key if found else None
        :rtype: None or Str
        """
        readme_key = None
        prefix = self.build_s3_key('')
        bucket_name = app.config['S3_BUCKET_NAME']
        s3_client = app.config['S3']
        response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
        for content in response['Contents']:
            if 'readme' in content['Key'].lower():
                readme_key = content['Key']
        return readme_key

    def get_all_metadata_name_for_publisher(self):
        bucket_name = app.config['S3_BUCKET_NAME']
        s3_client = app.config['S3']
        keys = []
        prefix = self.build_s3_base_prefix()
        list_objects = s3_client.list_objects(Bucket=bucket_name,
                                              Prefix=prefix)
        if list_objects is not None and 'Contents' in list_objects:
            for ob in s3_client.list_objects(Bucket=bucket_name,
                                             Prefix=prefix)['Contents']:
                keys.append(ob['Key'])
        return keys

    def build_s3_key(self, path):
        return "{prefix}/{path}"\
            .format(prefix=self.build_s3_versioned_prefix(),
                    path=path)

    def build_s3_base_prefix(self):
        return "{prefix}/{publisher}/{package}".\
            format(prefix=self.prefix,
                   publisher=self.publisher,
                   package=self.package)

    def build_s3_versioned_prefix(self):
        return "{prefix}/_v/{version}". \
            format(prefix=self.build_s3_base_prefix(),
                   version=self.version)

    def build_s3_object_url(self, domain_name, path):
        return 'https://bits.{base_url}.s3.amazonaws.com/{key}'.\
            format(base_url=domain_name,
                   key=self.build_s3_key(path))

    def generate_pre_signed_put_obj_url(self, path, md5, acl='public-read'):
        """
        This method produce a pre-signed url for a specific key to be used
        for uploading data at client side
        :param path: The relative path of the object
        :param md5: The md5 hash of the file to be uploaded
        :param acl: The canned acl to be used while put object operation
        :return: Pre-signed URL
        """
        bucket_name = app.config['S3_BUCKET_NAME']
        s3_client = app.config['S3']
        key = self.build_s3_key(path)
        params = {'Bucket': bucket_name, 'Key': key}
        url = s3_client.generate_presigned_url('put_object',
                                               Params=params,
                                               ExpiresIn=3600)
        return url

    def delete_data_package(self):
        """
        This method will delete all objects with the prefix
        generated by :func:`~app.mod_api.models.build_s3_prefix`.
        This method is used for Hard delete data packages.
        :return: Status True if able to delete or False if exception
        """
        try:
            bucket_name = app.config['S3_BUCKET_NAME']
            s3_client = app.config['S3']

            keys = []
            list_objects = s3_client.list_objects(Bucket=bucket_name,
                                                  Prefix=self.build_s3_base_prefix())
            if list_objects is not None and 'Contents' in list_objects:
                for ob in s3_client \
                    .list_objects(Bucket=bucket_name,
                                  Prefix=self.build_s3_base_prefix())['Contents']:
                    keys.append(dict(Key=ob['Key']))

            s3_client.delete_objects(Bucket=bucket_name, Delete=dict(Objects=keys))
            return True
        except Exception as e:
            app.logger.error(e)
            return False

    def change_acl(self, acl):
        """
        This method will change access for all objects with the prefix
        generated by :func:`~app.mod_api.models.build_s3_prefix`.
        This method is used for Soft delete data packages.
        :return: Status True if able to delete or False if exception
        """
        try:
            bucket_name = app.config['S3_BUCKET_NAME']
            s3_client = app.config['S3']

            keys = []
            list_objects = s3_client.list_objects(Bucket=bucket_name,
                                                  Prefix=self.build_s3_base_prefix())
            if list_objects is not None and 'Contents' in list_objects:
                for ob in s3_client \
                    .list_objects(Bucket=bucket_name,
                                  Prefix=self.build_s3_base_prefix())['Contents']:
                    keys.append(ob['Key'])

            for key in keys:
                s3_client.put_object_acl(Bucket=bucket_name, Key=key,
                                         ACL=acl)
        except Exception as e:
            app.logger.error(e)
            return False
        return True

    def copy_to_new_version(self, version):
        try:
            bucket_name = app.config['S3_BUCKET_NAME']
            s3_client = app.config['S3']
            latest_keys = []
            list_objects = s3_client.list_objects(Bucket=bucket_name,
                                                  Prefix=self.build_s3_versioned_prefix())
            if list_objects is not None and 'Contents' in list_objects:
                for ob in s3_client \
                    .list_objects(Bucket=bucket_name,
                                  Prefix=self.build_s3_versioned_prefix())['Contents']:
                    latest_keys.append(ob['Key'])
            for key in latest_keys:
                versioned_key = key.replace('/latest/', '/{0}/'.format(version))
                copy_source = {'Bucket': bucket_name, 'Key': key}
                s3_client.copy_object(Bucket=bucket_name,
                                      Key=versioned_key,
                                      CopySource=copy_source)
            return True
        except Exception as e:
            app.logger.error(e)
            return False


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

    packages = relationship("MetaDataDB", back_populates="publisher")

    users = relationship("PublisherUser", back_populates="publisher",
                         cascade='save-update, merge, delete, delete-orphan')


class User(db.Model):
    """
    This class is DB model for storing user attributes
    """

    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    email = db.Column(db.TEXT, index=True)
    secret = db.Column(db.TEXT)
    name = db.Column(db.TEXT, unique=True, index=True, nullable=False)
    full_name = db.Column(db.TEXT)
    auth0_id = db.Column(db.TEXT, index=True)
    sysadmin = db.Column(db.BOOLEAN, default=False)

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
    def create_or_update_user_from_callback(user_info):
        """
        This method populates db when user sign up or login through external auth system
        :param user_info: User data from external auth system
        :return: User data from Database
        """
        auth0_id = user_info['user_id']
        user = User.query.filter_by(auth0_id=auth0_id).first()
        if user is None:
            user = User()
            user.email = user_info['email']
            user.secret = os.urandom(24).encode('hex')
            user.name = user_info['username']
            user.auth0_id = auth0_id

            publisher = Publisher(name=user.name)
            association = PublisherUser(role=UserRoleEnum.owner)
            association.publisher = publisher
            user.publishers.append(association)

            db.session.add(user)
            db.session.commit()
        elif user.secret == 'supersecret':
            user.secret = os.urandom(24).encode('hex')
            db.session.add(user)
            db.session.commit()
        return user

    @staticmethod
    def get_userinfo_by_id(user_id):
        user = User.query.filter_by(id=user_id).first()
        if user:
            return user
        return None


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


class MetaDataDB(db.Model):
    """
    This class is DB model for storing package data
    """
    __tablename__ = "package"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    name = db.Column(db.TEXT, index=True)
    version = db.Column(db.TEXT, index=True, default='latest')
    descriptor = db.Column(db.JSON)
    status = db.Column(db.TEXT, index=True, default='active')
    private = db.Column(db.BOOLEAN, default=False)
    readme = db.Column(db.TEXT)

    publisher_id = db.Column(db.Integer, ForeignKey('publisher.id'))
    publisher = relationship("Publisher", back_populates="packages",
                             cascade="save-update, merge, delete, delete-orphan",
                             single_parent=True)

    __table_args__ = (
        UniqueConstraint("name", "version", "publisher_id"),
    )

    @staticmethod
    def create_or_update_version(publisher_name, package_name, version):
        try:
            data_latest = MetaDataDB.query.join(Publisher). \
                filter(Publisher.name == publisher_name,
                       MetaDataDB.name == package_name,
                       MetaDataDB.version == 'latest').one()
            instance = MetaDataDB.query.join(Publisher). \
                filter(Publisher.name == publisher_name,
                       MetaDataDB.name == package_name,
                       MetaDataDB.version == version).first()
            update_props = ['name', 'version', 'descriptor', 'status',
                            'private', 'readme', 'publisher_id']
            if instance is None:
                instance = MetaDataDB()

            for update_prop in update_props:
                setattr(instance, update_prop, getattr(data_latest, update_prop))
            instance.version = version

            db.session.add(instance)
            db.session.commit()
            return True
        except Exception as e:
            app.logger.error(e)
            return False

    @staticmethod
    def create_or_update(name, publisher_name, **kwargs):
        """
        This method creates data package of update data package attributes
        :param name: package name
        :param publisher_name: publisher name
        :param kwargs: package attribute names
        """
        pub_id = Publisher.query.filter_by(name=publisher_name).one().id
        instance = MetaDataDB.query.join(Publisher)\
            .filter(MetaDataDB.name == name,
                    Publisher.name == publisher_name).first()
        if not instance:
            instance = MetaDataDB(name=name)
            instance.publisher_id = pub_id
        for key, value in kwargs.items():
            setattr(instance, key, value)
        db.session.add(instance)
        db.session.commit()

    @staticmethod
    def change_status(publisher_name, package_name, status='deleted'):
        """
        This method changes status of the data package. This method used
        for soft delete the data package
        :param publisher_name: publisher name
        :param package_name: package name
        :param status: status of the package
        :return: If success True else False
        """
        if status not in ['deleted', 'active']:
            raise Exception('Invalid status name. '
                            'Only deleted and active are allowed')
        try:
            data = MetaDataDB.query.join(Publisher). \
                filter(Publisher.name == publisher_name,
                       MetaDataDB.name == package_name).one()
            data.status = status
            db.session.add(data)
            db.session.commit()
            return True
        except Exception as e:
            app.logger.error(e)
            return False

    @staticmethod
    def delete_data_package(publisher_name, package_name):
        """
        This method deletes the data package. This method used
        for hard delete the data package
        :param publisher_name: publisher name
        :param package_name: package name
        :return: If success True else False
        """
        try:
            data = MetaDataDB.query.join(Publisher). \
                filter(Publisher.name == publisher_name,
                       MetaDataDB.name == package_name).one()
            package_id = data.id
            meta_data = MetaDataDB.query.get(package_id)
            db.session.delete(meta_data)
            db.session.commit()
            return True
        except Exception as e:
            app.logger.error(e)
            return False

    @staticmethod
    def get_package(publisher_name, package_name):
        """
        This method returns certain data packages belongs to a publisher
        :param publisher_name: publisher name
        :param package_name: package name
        :return: data package object based on the filter.
        """
        try:
            instance = MetaDataDB.query.join(Publisher) \
                .filter(MetaDataDB.name == package_name,
                        Publisher.name == publisher_name).first()
            return instance
        except Exception as e:
            app.logger.error(e)
            return None
