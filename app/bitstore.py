# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import json

from flask import current_app as app
from botocore.exceptions import ClientError


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
        :return: The String value of the datapackage.json or None if not found
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
        except ClientError as e:
            if e.response['Error']['Code'] != 'NoSuchKey':
                raise e
            return None

    def get_readme_object_key(self):
        """
        This method search for any readme object is present for the
        generated prefix by:
        >>> BitStore.build_s3_key()
        :return: Value of the readme key if found else None
        :rtype: None or Str
        """
        readme_key = 'None'
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

    def build_s3_key(self, path=None):
        if not path:
            return self.build_s3_versioned_prefix()
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

    def build_s3_object_url(self, path=None):
        return '{base_url}/{key}'.\
            format(base_url=app.config['BITSTORE_URL'],
                   key=self.build_s3_key(path))

    def generate_pre_signed_post_object(self, md5, path=None,
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


    def change_acl(self, acl):
        """
        This method will change access for all objects with the prefix
        generated by :func:`~app.mod_api.models.build_s3_prefix`.
        This method is used for Soft delete data packages.
        :return: Status True if able to delete or False if exception
        """
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
        return True

    def copy_to_new_version(self, version):
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

    @staticmethod
    def extract_information_from_s3_url(url):
        information = url.split('metadata/')[1].split('/')
        publisher, package, version = information[0], information[1], information[3]
        return publisher, package, version
