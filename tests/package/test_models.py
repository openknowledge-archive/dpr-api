# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import boto3
from urlparse import urlparse
from moto import mock_s3
import unittest
import json
from app import create_app
from app.database import db
from app.package.models import BitStore, Package, PackageStateEnum
from app.profile.models import User, Publisher, UserRoleEnum, PublisherUser


class BitStoreTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()

    def test_metadata_s3_key(self):
        metadata = BitStore(publisher="pub_test", package="test_package")
        expected = "{t}/pub_test/test_package/_v/latest/datapackage.json".\
                   format(t=metadata.prefix)
        self.assertEqual(expected, metadata.build_s3_key('datapackage.json'))

    def test_metadata_s3_prefix(self):
        metadata = BitStore(publisher="pub_test", package="test_package")
        expected = "{t}/pub_test/test_package".format(t=metadata.prefix)
        self.assertEqual(expected, metadata.build_s3_base_prefix())

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
            obs_list = list(s3.list_objects(Bucket=bucket_name, Prefix=key).\
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
            post = metadata.generate_pre_signed_post_object('datapackage.json',
                                                            123)
            parsed = urlparse(post['url'])
            self.assertEqual(parsed.netloc,
                             's3-{region}.amazonaws.com'.
                             format(region=self.app.config['AWS_REGION']))
            self.assertEqual('public-read', post['fields']['acl'])

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
            self.assertEqual(bit_store.get_readme_object_key(), None)

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
            self.assertEqual(bit_store.get_s3_object(None), None)

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

            # for grant in res['Grants']:
            #     self.assertTrue(grant['Permission'] ==
            #                     public_grants[grant['Grantee']['Type']])
            #
            bit_store.change_acl("private")
            res = s3.get_object_acl(Bucket=bucket_name, Key=metadata_key)
            full_control = filter(lambda grant: grant['Permission'] == 'FULL_CONTROL', res['Grants'])
            self.assertEqual(len(full_control), 1)
            self.assertEqual(full_control[0].get('Grantee')['ID'], owner_id)
            read_control = filter(lambda grant: grant['Permission'] == 'READ', res['Grants'])
            self.assertEqual(len(read_control), 0)
            #
            # for grant in res['Grants']:
            #     self.assertTrue(grant['Permission'] ==
            #                     private_grants[grant['Grantee']['Type']])
            #
            # bit_store.change_acl("public-read")
            # res = s3.get_object_acl(Bucket=bucket_name, Key=metadata_key)
            #
            # for grant in res['Grants']:
            #     self.assertTrue(grant['Permission'] ==
            #                     public_grants[grant['Grantee']['Type']])

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


class PackageTestCase(unittest.TestCase):
    def setUp(self):
        self.publisher_one = 'test_publisher1'
        self.publisher_two = 'test_publisher2'
        self.package_one = 'test_package1'
        self.package_two = 'test_package2'
        self.app = create_app()
        self.app.app_context().push()

        with self.app.test_request_context():
            db.drop_all()
            db.create_all()

            user1 = User(name=self.publisher_one)
            publisher1 = Publisher(name=self.publisher_one)
            association1 = PublisherUser(role=UserRoleEnum.owner)
            association1.publisher = publisher1
            user1.publishers.append(association1)

            user2 = User(name=self.publisher_two)
            publisher2 = Publisher(name=self.publisher_two)
            association2 = PublisherUser(role=UserRoleEnum.owner)
            association2.publisher = publisher2
            user2.publishers.append(association2)

            metadata1 = Package(name=self.package_one)
            metadata1.descriptor = json.dumps(dict(name='test_one'))
            publisher1.packages.append(metadata1)

            metadata2 = Package(name=self.package_two)
            metadata2.descriptor = json.dumps(dict(name='test_two'))
            publisher1.packages.append(metadata2)

            metadata3 = Package(name=self.package_one)
            metadata3.descriptor = json.dumps(dict(name='test_three'))
            publisher2.packages.append(metadata3)

            metadata4 = Package(name=self.package_two)
            metadata4.descriptor = json.dumps(dict(name='test_four'))
            publisher2.packages.append(metadata4)

            db.session.add(user1)
            db.session.add(user2)

            db.session.commit()

    def test_composite_key(self):
        res = Package.query.join(Publisher).filter(Publisher.name ==
                                                   self.publisher_one).all()
        self.assertEqual(2, len(res))

    def test_update_fields_if_instance_present(self):
        metadata = Package.query.join(Publisher)\
            .filter(Publisher.name == self.publisher_one,
                    Package.name == self.package_one).one()
        self.assertEqual(json.loads(metadata.descriptor)['name'], "test_one")
        Package.create_or_update(self.package_one, self.publisher_one,
                                 descriptor=json.dumps(dict(name='sub')),
                                 private=True)
        metadata = Package.query.join(Publisher) \
            .filter(Publisher.name == self.publisher_one,
                    Package.name == self.package_one).one()
        self.assertEqual(json.loads(metadata.descriptor)['name'], "sub")
        self.assertEqual(metadata.private, True)

    def test_insert_if_not_present(self):
        pub = self.publisher_two
        name = "custom_name"

        metadata = Package.query.join(Publisher) \
            .filter(Publisher.name == pub,
                    Package.name == name).all()
        self.assertEqual(len(metadata), 0)
        Package.create_or_update(name, pub,
                                 descriptor=json.dumps(dict(name='sub')),
                                 private=True)
        metadata = Package.query.join(Publisher) \
            .filter(Publisher.name == pub,
                    Package.name == name).all()
        self.assertEqual(len(metadata), 1)

    def test_change_status(self):
        data = Package.query.join(Publisher). \
            filter(Publisher.name == self.publisher_one,
                   Package.name == self.package_one).one()
        self.assertEqual(PackageStateEnum.active, data.status)

        Package.change_status(self.publisher_one, self.package_one, PackageStateEnum.deleted)

        data = Package.query.join(Publisher). \
            filter(Publisher.name == self.publisher_one,
                   Package.name == self.package_one).one()
        self.assertEqual(PackageStateEnum.deleted, data.status)

        Package.change_status(self.publisher_one, self.package_one,
                              status=PackageStateEnum.active)

        data = Package.query.join(Publisher). \
            filter(Publisher.name == self.publisher_one,
                   Package.name == self.package_one).one()
        self.assertEqual(PackageStateEnum.active, data.status)

    def test_return_false_if_failed_to_change_status(self):
        status = Package.change_status(self.publisher_one, 'fake_package',
                                       status='active')
        self.assertFalse(status)

    def test_return_true_if_delete_data_package_success(self):
        status = Package.delete_data_package(self.publisher_one,
                                             self.package_one)
        self.assertTrue(status)
        data = Package.query.join(Publisher). \
            filter(Publisher.name == self.publisher_one,
                   Package.name == self.package_one).all()
        self.assertEqual(0, len(data))
        data = Publisher.query.all()
        self.assertEqual(1, len(data))

    def test_return_false_if_error_occur(self):
        status = Package.delete_data_package("fake_package",
                                             self.package_one)
        self.assertFalse(status)

    def test_should_populate_new_versioned_data_package(self):
        Package.create_or_update_version(self.publisher_one,
                                         self.package_two, 'tag_one')
        latest_data = Package.query.join(Publisher). \
            filter(Publisher.name == self.publisher_one,
                   Package.name == self.package_two,
                   Package.version == 'latest').one()
        tagged_data = Package.query.join(Publisher). \
            filter(Publisher.name == self.publisher_one,
                   Package.name == self.package_two,
                   Package.version == 'tag_one').one()
        self.assertEqual(latest_data.name, tagged_data.name)
        self.assertEqual('tag_one', tagged_data.version)

    def test_should_update_data_package_if_preexists(self):
        with self.app.test_request_context():
            pub = Publisher.query.filter_by(name=self.publisher_one).one()
            pub.packages.append(Package(name=self.package_two,
                                        version='tag_one',
                                        readme='old_readme'))
            db.session.add(pub)
            db.session.commit()
        latest_data = Package.query.join(Publisher). \
            filter(Publisher.name == self.publisher_one,
                   Package.name == self.package_two,
                   Package.version == 'latest').one()
        tagged_data = Package.query.join(Publisher). \
            filter(Publisher.name == self.publisher_one,
                   Package.name == self.package_two,
                   Package.version == 'tag_one').one()
        self.assertNotEqual(latest_data.readme, tagged_data.readme)

        Package.create_or_update_version(self.publisher_one,
                                         self.package_two,
                                         'tag_one')
        tagged_data = Package.query.join(Publisher). \
            filter(Publisher.name == self.publisher_one,
                   Package.name == self.package_two,
                   Package.version == 'tag_one').one()
        self.assertEqual(latest_data.readme, tagged_data.readme)

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
