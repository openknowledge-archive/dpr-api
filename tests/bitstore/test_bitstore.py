# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import boto3
import unittest

from urlparse import urlparse
from moto import mock_s3
from app import create_app
from app.bitstore import BitStore


class BitStoreTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()

    def test_metadata_s3_key(self):
        metadata = BitStore(publisher="pub_test", package="test_package")
        expected = "{t}/pub_test/test_package/_v/latest/datapckage.json". \
            format(t=metadata.prefix)
        self.assertEqual(expected, metadata.build_s3_key('datapckage.json'))

    def test_metadata_s3_prefix(self):
        metadata = BitStore(publisher="pub_test", package="test_package")
        expected = "{t}/pub_test/test_package".format(t=metadata.prefix)
        self.assertEqual(expected, metadata.build_s3_base_prefix())

    def test_extract_information_from_s3_url(self):
        metadata = BitStore(publisher="pub_test", package="test_package")
        s3_key = metadata.build_s3_key('datapckage.json')
        pub, package, version = BitStore.extract_information_from_s3_url(s3_key)
        self.assertEqual(pub, 'pub_test')
        self.assertEqual(package, 'test_package')
        self.assertEqual(version, 'latest')

    @mock_s3
    def test_save(self):
        with self.app.app_context():
            s3 = boto3.client('s3')
            bucket_name = self.app.config['S3_BUCKET_NAME']
            s3.create_bucket(Bucket=bucket_name)
            metadata = BitStore(publisher="pub_test",
                                package="test_package",
                                body='hi')
            key = metadata.build_s3_key('datapackage.json')
            metadata.save_metadata()
            obs_list = list(s3.list_objects(Bucket=bucket_name, Prefix=key). \
                            get('Contents'))
            self.assertEqual(1, len(obs_list))
            self.assertEqual(key, obs_list[0]['Key'])
            res = s3.get_object_acl(Bucket=bucket_name, Key=key)

            owner_id = res['Owner']['ID']
            aws_all_user_group_url = 'http://acs.amazonaws.com/groups/global/AllUsers'

            full_control = filter(lambda grant: grant['Permission'] == 'FULL_CONTROL', res['Grants'])
            self.assertEqual(len(full_control), 1)
            self.assertEqual(full_control[0].get('Grantee')['ID'], owner_id)

            read_control = filter(lambda grant: grant['Permission'] == 'READ', res['Grants'])
            self.assertEqual(len(read_control), 1)
            self.assertEqual(read_control[0].get('Grantee')['URI'], aws_all_user_group_url)

    @mock_s3
    def test_get_metadata_body(self):
        with self.app.app_context():
            s3 = boto3.client('s3')
            bucket_name = self.app.config['S3_BUCKET_NAME']
            s3.create_bucket(Bucket=bucket_name)
            metadata = BitStore(publisher="pub_test",
                                package="test_package",
                                body='hi')
            s3.put_object(
                Bucket=bucket_name,
                Key=metadata.build_s3_key('datapackage.json'),
                Body=metadata.body)
            self.assertEqual(metadata.body, metadata.get_metadata_body())

    @mock_s3
    def test_get_all_metadata_name_for_publisher(self):
        with self.app.app_context():
            s3 = boto3.client('s3')
            bucket_name = self.app.config['S3_BUCKET_NAME']
            s3.create_bucket(Bucket=bucket_name)
            metadata = BitStore(publisher="pub_test",
                                package="test_package",
                                body='hi')
            s3.put_object(
                Bucket=bucket_name,
                Key=metadata.build_s3_key('datapackage.json'),
                Body=metadata.body)
            self.assertEqual(1, len(metadata.get_all_metadata_name_for_publisher()))

    @mock_s3
    def test_get_empty_metadata_name_for_publisher(self):
        with self.app.app_context():
            s3 = boto3.client('s3')
            bucket_name = self.app.config['S3_BUCKET_NAME']
            s3.create_bucket(Bucket=bucket_name)
            metadata = BitStore(publisher="pub_test",
                                package="test_package",
                                body='hi')
            s3.put_object(Bucket=bucket_name,
                          Key='test/key.json',
                          Body=metadata.body)
            self.assertEqual(0, len(metadata.get_all_metadata_name_for_publisher()))

    @mock_s3
    def test_generate_pre_signed_put_obj_url(self):
        with self.app.app_context():
            s3 = boto3.client('s3')
            bucket_name = self.app.config['S3_BUCKET_NAME']
            s3.create_bucket(Bucket=bucket_name)

            metadata = BitStore(publisher="pub_test",
                                package="test_package",
                                body='hi')
            post = metadata.generate_pre_signed_post_object(123, 'datapackage.json')
            parsed = urlparse(post['url'])
            self.assertEqual(parsed.netloc,
                             's3-{region}.amazonaws.com'.
                             format(region=self.app.config['AWS_REGION']))
            self.assertEqual('public-read', post['fields']['acl'])
            self.assertEqual('text/plain', post['fields']['Content-Type'])

    @mock_s3
    def test_get_readme_object_key(self):
        with self.app.app_context():
            bit_store = BitStore('test_pub', 'test_package')
            s3 = boto3.client('s3')
            bucket_name = self.app.config['S3_BUCKET_NAME']
            s3.create_bucket(Bucket=bucket_name)
            read_me_key = bit_store.build_s3_key('readme.md')
            s3.put_object(Bucket=bucket_name, Key=read_me_key, Body='')
            self.assertEqual(bit_store.get_readme_object_key(), read_me_key)

    @mock_s3
    def test_return_none_if_no_readme_found(self):
        with self.app.app_context():
            bit_store = BitStore('test_pub', 'test_package')
            s3 = boto3.client('s3')
            bucket_name = self.app.config['S3_BUCKET_NAME']
            s3.create_bucket(Bucket=bucket_name)
            read_me_key = bit_store.build_s3_key('test.md')
            s3.put_object(Bucket=bucket_name, Key=read_me_key, Body='')
            self.assertEqual(bit_store.get_readme_object_key(), 'None')

    @mock_s3
    def test_return_none_if_object_found(self):
        with self.app.app_context():
            bit_store = BitStore('test_pub', 'test_package')
            s3 = boto3.client('s3')
            bucket_name = self.app.config['S3_BUCKET_NAME']
            s3.create_bucket(Bucket=bucket_name)
            read_me_key = bit_store.build_s3_key('test.md')
            s3.put_object(Bucket=bucket_name, Key=read_me_key, Body='')
            self.assertEqual(bit_store.get_s3_object(read_me_key + "testing"), None)
            self.assertEqual(bit_store.get_s3_object('None'), None)

    @mock_s3
    def test_change_acl(self):
        with self.app.app_context():
            public_grants = {
                'CanonicalUser': 'FULL_CONTROL',
                'Group': 'READ'
            }
            private_grants = {'CanonicalUser': 'FULL_CONTROL'}
            bit_store = BitStore('test_pub', 'test_package', body='test')
            s3 = boto3.client('s3')
            bucket_name = self.app.config['S3_BUCKET_NAME']
            s3.create_bucket(Bucket=bucket_name)
            metadata_key = bit_store.build_s3_key('datapackage.json')

            bit_store.save_metadata()

            res = s3.get_object_acl(Bucket=bucket_name, Key=metadata_key)

            owner_id = res['Owner']['ID']
            aws_all_user_group_url = 'http://acs.amazonaws.com/groups/global/AllUsers'

            full_control = filter(lambda grant: grant['Permission'] == 'FULL_CONTROL', res['Grants'])
            self.assertEqual(len(full_control), 1)
            self.assertEqual(full_control[0].get('Grantee')['ID'], owner_id)

            read_control = filter(lambda grant: grant['Permission'] == 'READ', res['Grants'])
            self.assertEqual(len(read_control), 1)
            self.assertEqual(read_control[0].get('Grantee')['URI'], aws_all_user_group_url)

            bit_store.change_acl("private")
            res = s3.get_object_acl(Bucket=bucket_name, Key=metadata_key)
            full_control = filter(lambda grant: grant['Permission'] == 'FULL_CONTROL', res['Grants'])
            self.assertEqual(len(full_control), 1)
            self.assertEqual(full_control[0].get('Grantee')['ID'], owner_id)
            read_control = filter(lambda grant: grant['Permission'] == 'READ', res['Grants'])
            self.assertEqual(len(read_control), 0)

    @mock_s3
    def test_delete_data_package(self):
        with self.app.app_context():
            bit_store = BitStore('test_pub', 'test_package')
            s3 = boto3.client('s3')
            bucket_name = self.app.config['S3_BUCKET_NAME']
            s3.create_bucket(Bucket=bucket_name)
            read_me_key = bit_store.build_s3_key('test.md')
            data_key = bit_store.build_s3_key('data.csv')
            metadata_key = bit_store.build_s3_key('datapackage.json')
            s3.put_object(Bucket=bucket_name, Key=read_me_key, Body='readme')
            s3.put_object(Bucket=bucket_name, Key=data_key, Body='data')
            s3.put_object(Bucket=bucket_name, Key=metadata_key, Body='metedata')
            status = bit_store.delete_data_package()
            read_me_res = s3.list_objects(Bucket=bucket_name, Prefix=read_me_key)
            self.assertTrue('Contents' not in read_me_res)

            data_res = s3.list_objects(Bucket=bucket_name, Prefix=data_key)
            self.assertTrue('Contents' not in data_res)
            self.assertTrue(status)

    @mock_s3
    def test_should_return_true_delete_data_package_if_data_not_exists(self):
        with self.app.app_context():
            bit_store = BitStore('test_pub', 'test_package')
            s3 = boto3.client('s3')
            bucket_name = self.app.config['S3_BUCKET_NAME']
            s3.create_bucket(Bucket=bucket_name)
            read_me_key = bit_store.build_s3_key('test.md')
            data_key = bit_store.build_s3_key('data.csv')
            metadata_key = bit_store.build_s3_key('datapackage.json')

            status = bit_store.delete_data_package()
            read_me_res = s3.list_objects(Bucket=bucket_name, Prefix=read_me_key)
            self.assertTrue('Contents' not in read_me_res)

            data_res = s3.list_objects(Bucket=bucket_name, Prefix=data_key)
            self.assertTrue('Contents' not in data_res)

            metadata_res = s3.list_objects(Bucket=bucket_name, Prefix=metadata_key)
            self.assertTrue('Contents' not in metadata_res)

            self.assertTrue(status)

    @mock_s3
    def test_should_copy_all_object_from_latest_to_tag(self):
        numeric_version = 0.8
        with self.app.app_context():
            bit_store = BitStore('test_pub', 'test_package')
            s3 = boto3.client('s3')
            bucket_name = self.app.config['S3_BUCKET_NAME']
            s3.create_bucket(Bucket=bucket_name)

            read_me_key = bit_store.build_s3_key('test.md')
            data_key = bit_store.build_s3_key('data.csv')
            metadata_key = bit_store.build_s3_key('datapackage.json')
            s3.put_object(Bucket=bucket_name, Key=read_me_key, Body='readme')
            s3.put_object(Bucket=bucket_name, Key=data_key, Body='data')
            s3.put_object(Bucket=bucket_name, Key=metadata_key, Body='metedata')

            bit_store.copy_to_new_version(numeric_version)

            bit_store_numeric = BitStore('test_pub', 'test_package',
                                         numeric_version)
            objects_nu = s3.list_objects(Bucket=bucket_name,
                                         Prefix=bit_store_numeric
                                         .build_s3_versioned_prefix())
            objects_old = s3.list_objects(Bucket=bucket_name,
                                          Prefix=bit_store
                                          .build_s3_versioned_prefix())
            self.assertEqual(len(objects_nu['Contents']),
                             len(objects_old['Contents']))
