# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import json
import os
import datetime
from botocore.exceptions import ClientError, ParamValidationError
from sqlalchemy import ForeignKey
from sqlalchemy import UniqueConstraint

from sqlalchemy.dialects.postgresql import JSON
from flask import current_app as app
from sqlalchemy.orm import relationship

from app.database import db


class BitStore(object):
    prefix = 'metadata'

    def __init__(self, publisher, package='', version='latest', body=None):
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

    def save(self):
        bucket_name = app.config['S3_BUCKET_NAME']
        s3_client = app.config['S3']
        key = self.build_s3_key('datapackage.json')
        s3_client.put_object(Bucket=bucket_name, Key=key, Body=self.body)

    def get_metadata_body(self):
        key = self.build_s3_key('datapackage.json')
        return self.get_s3_object(key)

    def get_s3_object(self, key):
        try:
            bucket_name = app.config['S3_BUCKET_NAME']
            s3_client = app.config['S3']
            response = s3_client.get_object(Bucket=bucket_name, Key=key)
            return response['Body'].read()
        except ClientError or ParamValidationError:
            return None

    def get_readme_object_key(self):
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
        prefix = self.build_s3_prefix()
        list_objects = s3_client.list_objects(Bucket=bucket_name,
                                              Prefix=prefix)
        if list_objects is not None and 'Contents' in list_objects:
            for ob in s3_client.list_objects(Bucket=bucket_name,
                                             Prefix=prefix)['Contents']:
                keys.append(ob['Key'])
        return keys

    def build_s3_key(self, path):
        return "{prefix}/{publisher}/{package}/_v/{version}/{path}"\
            .format(prefix=self.prefix, publisher=self.publisher,
                    package=self.package, version=self.version, path=path)

    def build_s3_prefix(self):
        return "{prefix}/{publisher}".\
            format(prefix=self.prefix, publisher=self.publisher)

    def generate_pre_signed_put_obj_url(self, path):
        bucket_name = app.config['S3_BUCKET_NAME']
        s3_client = app.config['S3']
        key = self.build_s3_key(path)
        params = {'Bucket': bucket_name, 'Key': key}
        url = s3_client.generate_presigned_url('put_object',
                                               Params=params,
                                               ExpiresIn=3600)
        return url


class Publisher(db.Model):
    __tablename__ = 'publisher'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    name = db.Column(db.TEXT, unique=True, index=True, nullable=False)
    title = db.Column(db.Text)

    packages = relationship("MetaDataDB", back_populates="publisher")

    users = relationship("PublisherUser", back_populates="publisher")


class User(db.Model):

    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    email = db.Column(db.TEXT, index=True)
    secret = db.Column(db.TEXT)
    name = db.Column(db.TEXT, unique=True, index=True, nullable=False)
    full_name = db.Column(db.TEXT)
    auth0_id = db.Column(db.TEXT, index=True)

    publishers = relationship("PublisherUser", back_populates="user")

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
        auth0_id = user_info['user_id']
        user = User.query.filter_by(auth0_id=auth0_id).first()
        if user is None:
            user = User()
            user.email = user_info['email']
            user.secret = os.urandom(24).encode('hex')
            user.user_id = user_info['user_id']
            user.user_name = user_info['username']
            user.auth0_id = auth0_id

            publisher = Publisher(name=user.user_name)
            association = PublisherUser(role="OWNER")
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


class PublisherUser(db.Model):
    __tablename__ = 'publisher_user'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    user_id = db.Column(db.Integer, ForeignKey('user.id'), primary_key=True)
    publisher_id = db.Column(db.Integer, ForeignKey('publisher.id'), primary_key=True)

    role = db.Column(db.TEXT, nullable=False)

    publisher = relationship("Publisher", back_populates="users")
    user = relationship("User", back_populates="publishers")


class MetaDataDB(db.Model):
    __tablename__ = "package"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    name = db.Column(db.TEXT, index=True)
    descriptor = db.Column(JSON)
    status = db.Column(db.TEXT, index=True)
    private = db.Column(db.Boolean)
    readme = db.Column(db.TEXT)

    publisher_id = db.Column(db.Integer, ForeignKey('publisher.id'))
    publisher = relationship("Publisher", back_populates="packages")

    __table_args__ = (
        UniqueConstraint("name", "publisher_id"),
    )

    @staticmethod
    def create_or_update(name, publisher_name, **kwargs):
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
