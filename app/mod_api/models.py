# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import json
import os

from botocore.exceptions import ClientError, ParamValidationError
from sqlalchemy import UniqueConstraint

from sqlalchemy.dialects.postgresql import JSON
from flask import current_app as app
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


class User(db.Model):

    __tablename__ = 'user'

    user_id = db.Column(db.String(64), primary_key=True)
    email = db.Column(db.String(128), index=True)
    secret = db.Column(db.String(64))
    user_name = db.Column(db.String(64))

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'user_id': self.user_id,
            'email': self.email,
            'name': self.user_name,
            'secret': self.secret
        }

    @staticmethod
    def create_or_update_user_from_callback(user_info):
        user_id = user_info['user_id']
        user = User.query.filter_by(user_id=user_id).first()
        if user is None:
            user = User()
            user.email = user_info['email']
            user.secret = os.urandom(24).encode('hex')
            user.user_id = user_info['user_id']
            user.user_name = user_info['username']
            db.session.add(user)
            db.session.commit()
        elif user.secret == 'supersecret':
            user.secret = os.urandom(24).encode('hex')
            db.session.add(user)
            db.session.commit()
        return user

    @staticmethod
    def get_userinfo_by_id(user_id):
        user = User.query.filter_by(user_id=user_id).first()
        if user:
            return user
        return None


class MetaDataDB(db.Model):
    __tablename__ = "packages"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    publisher = db.Column(db.String(64))
    descriptor = db.Column(JSON)
    status = db.Column(db.String(16))
    private = db.Column(db.Boolean)
    readme = db.Column(db.TEXT)

    __table_args__ = (
        UniqueConstraint("name", "publisher"),
    )

    def __init__(self, name, publisher):
        self.name = name
        self.publisher = publisher

    @staticmethod
    def create_or_update(name, publisher, **kwargs):
        instance = MetaDataDB.query.filter_by(name=name,
                                              publisher=publisher).first()
        if not instance:
            instance = MetaDataDB(name, publisher)

        for key, value in kwargs.items():
            setattr(instance, key, value)
        db.session.add(instance)
        db.session.commit()
