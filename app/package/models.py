# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import json
import datetime

import enum
from sqlalchemy import ForeignKey
from sqlalchemy import UniqueConstraint
from flask import current_app as app
from sqlalchemy.orm import relationship
from app.profile.models import Publisher
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
        >>> BitStore.build_s3_key()
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
        return 'https://bits-{base_url}/{key}'.\
            format(base_url=domain_name,
                   key=self.build_s3_key(path))

    def generate_pre_signed_post_object(self, path, md5,
                                        acl='public-read'):
        """
        This method produce required data to upload file from client side
        for uploading data at client side. The Content-Type is set to
        text/plain for any type of file. This will avoid security risks (e.g.
        someone uploading html with malicious JS in it and then users
        opening that file as html).

        :param path: The relative path of the object
        :param md5: The md5 hash of the file to be uploaded

        :param acl: The object ACL default is public_read
        :return: dict containing S3 url and post params
        """
        bucket_name = app.config['S3_BUCKET_NAME']
        s3_client = app.config['S3']
        key = self.build_s3_key(path)
        post = s3_client.generate_presigned_post(Bucket=bucket_name,
                                                 Key=key,
                                                 Fields={
                                                    'acl': acl,
                                                    'Content-MD5': str(md5),
                                                    'Content-Type': 'text/plain'},
                                                 Conditions=[
                                                  {"acl": "public-read"},
                                                  ["starts-with", "$Content-Type", ""],
                                                  ["starts-with", "$Content-MD5", ""]
                                                 ])
        return post

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

    @staticmethod
    def extract_information_from_s3_url(url):
        information = url.split('metadata/')[1].split('/')
        publisher, package, version = information[0], information[1], information[3]
        return publisher, package, version


class PackageStateEnum(enum.Enum):
    active = "ACTIVE"
    deleted = "DELETED"


class Package(db.Model):
    """
    This class is DB model for storing package data
    """
    __tablename__ = "package"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    name = db.Column(db.TEXT, index=True)
    status = db.Column(db.Enum(PackageStateEnum, native_enum=False),
                       index=True, default=PackageStateEnum.active)
    private = db.Column(db.BOOLEAN, default=False)

    publisher_id = db.Column(db.Integer, ForeignKey('publisher.id', ondelete='CASCADE'))
    publisher = relationship("Publisher", back_populates="packages",
                             cascade="save-update, merge, delete, delete-orphan",
                             single_parent=True)

    tags = relationship("PackageTag", back_populates="package")

    __table_args__ = (
        UniqueConstraint("name", "publisher_id"),
    )

    @staticmethod
    def create_or_update_tag(publisher_name, package_name, tag):
        try:
            package = Package.query.join(Publisher)\
                .filter(Publisher.name == publisher_name,
                        Package.name == package_name).one()

            data_latest = PackageTag.query.join(Package)\
                .filter(Package.id == package.id,
                        PackageTag.tag == 'latest').one()

            tag_instance = PackageTag.query.join(Package) \
                .filter(Package.id == package.id,
                        PackageTag.tag == tag).first()

            update_props = ['descriptor', 'readme', 'package_id']
            if tag_instance is None:
                tag_instance = PackageTag()

            for update_prop in update_props:
                setattr(tag_instance, update_prop, getattr(data_latest, update_prop))
            tag_instance.tag = tag

            db.session.add(tag_instance)
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
        instance = Package.query.join(Publisher)\
            .filter(Package.name == name,
                    Publisher.name == publisher_name).first()

        if not instance:
            instance = Package(name=name)
            instance.publisher_id = pub_id
            tag_instance = PackageTag()
            instance.tags.append(tag_instance)
        else:
            tag_instance = PackageTag.query.join(Package) \
                .filter(Package.id == instance.id,
                        PackageTag.tag == 'latest').one()
        for key, value in kwargs.items():
            if key not in ['descriptor', 'readme']:
                setattr(instance, key, value)
            else:
                setattr(tag_instance, key, value)
        db.session.add(instance)
        db.session.commit()

    @staticmethod
    def change_status(publisher_name, package_name, status=PackageStateEnum.active):
        """
        This method changes status of the data package. This method used
        for soft delete the data package
        :param publisher_name: publisher name
        :param package_name: package name
        :param status: status of the package
        :return: If success True else False
        """
        try:
            data = Package.query.join(Publisher). \
                filter(Publisher.name == publisher_name,
                       Package.name == package_name).one()
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
            data = Package.query.join(Publisher). \
                filter(Publisher.name == publisher_name,
                       Package.name == package_name).one()
            package_id = data.id
            Package.query.filter(Package.id == package_id).delete()
            # db.session.delete(meta_data)
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
            instance = Package.query.join(Publisher) \
                .filter(Package.name == package_name,
                        Publisher.name == publisher_name).first()
            return instance
        except Exception as e:
            app.logger.error(e)
            return None

    @staticmethod
    def is_package_exists(publisher_name, package_name):
        """
        This method will check package with the name already exists or not
        :param publisher_name: publisher name
        :param package_name: package name
        :return: True is data already exists else false
        """
        instance = Package.query.join(Publisher)\
            .filter(Package.name == package_name,
                    Publisher.name == publisher_name).all()
        return len(instance) > 0


class PackageTag(db.Model):

    __tablename__ = 'package_tag'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    tag = db.Column(db.TEXT, index=True, default='latest')
    tag_description = db.Column(db.Text)

    descriptor = db.Column(db.JSON)
    readme = db.Column(db.TEXT)

    package_id = db.Column(db.Integer, ForeignKey("package.id", ondelete='CASCADE'))

    package = relationship("Package", back_populates="tags",
                           cascade="save-update, merge, delete, delete-orphan",
                           single_parent=True)

    __table_args__ = (
        UniqueConstraint("tag", "package_id"),
    )
