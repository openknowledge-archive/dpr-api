# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import unittest
import json
import boto3
from mock import patch
from moto import mock_s3
from app import create_app
from app.database import db
from app.package.models import User, MetaDataDB, Publisher, \
    PublisherUser, UserRoleEnum, BitStore


class GetMetaDataTestCase(unittest.TestCase):
    def setUp(self):
        self.publisher = 'test_publisher'
        self.package = 'test_package'
        self.app = create_app()
        self.client = self.app.test_client()
        with self.app.app_context():
            db.drop_all()
            db.create_all()

    def test_throw_404_if_meta_data_not_found(self):
        response = self.client.\
            get('/api/package/%s/%s' % (self.publisher, self.package))
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(data['error_code'], 'DATA_NOT_FOUND')

    def test_return_200_if_meta_data_found(self):
        descriptor = {'name': 'test description'}
        with self.app.app_context():
            publisher = Publisher(name=self.publisher)
            metadata = MetaDataDB(name=self.package)
            metadata.descriptor = json.dumps(descriptor)
            publisher.packages.append(metadata)
            db.session.add(publisher)
            db.session.commit()
        response = self.client.\
            get('/api/package/%s/%s' % (self.publisher, self.package))
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        
    def test_return_all_metadata_is_there(self):
        descriptor = {'name': 'test description'}
        readme = 'README'
        with self.app.app_context():
            publisher = Publisher(name=self.publisher)
            metadata = MetaDataDB(name=self.package)
            metadata.descriptor = json.dumps(descriptor)
            metadata.readme = readme
            publisher.packages.append(metadata)
            db.session.add(publisher)
            db.session.commit()
        response = self.client.get('/api/package/%s/%s'%\
                                   (self.publisher, self.package))
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data), 5)
        self.assertEqual(data['descriptor']['name'], 'test description')
        self.assertEqual(data['readme'], 'README')
        self.assertEqual(data['id'], 1)
        self.assertEqual(data['name'], self.package)
        self.assertEqual(data['publisher'], self.publisher)

    def test_return_empty_string_if_readme_not_there(self):
        descriptor = {'name': 'test description'}
        with self.app.app_context():
            publisher = Publisher(name=self.publisher)
            metadata = MetaDataDB(name=self.package)
            metadata.descriptor = json.dumps(descriptor)
            publisher.packages.append(metadata)
            db.session.add(publisher)
            db.session.commit()
        response = self.client.get('/api/package/%s/%s'%\
                                   (self.publisher, self.package))
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200) 
        self.assertEqual(data['readme'], '')

    def test_return_generic_error_if_descriptor_is_not_json(self):
        descriptor = 'test description'
        with self.app.app_context():
            publisher = Publisher(name='pub')
            metadata = MetaDataDB(name=self.package)
            metadata.descriptor = descriptor
            publisher.packages.append(metadata)
            db.session.add(publisher)
            db.session.commit()
        response = self.client\
            .get('/api/package/%s/%s' % ('pub', self.package))
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(data['error_code'], 'GENERIC_ERROR')

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()


class GetAllMetaDataTestCase(unittest.TestCase):
    def setUp(self):
        self.publisher = 'test_publisher'
        self.package1 = 'test_package1'
        self.package2 = 'test_package2'
        self.app = create_app()
        self.client = self.app.test_client()
        with self.app.app_context():
            db.drop_all()
            db.create_all()
            publisher = Publisher(name=self.publisher)
            metadata1 = MetaDataDB(name=self.package1)
            metadata2 = MetaDataDB(name=self.package2)
            publisher.packages.append(metadata1)
            publisher.packages.append(metadata2)
            db.session.add(publisher)
            db.session.commit()

    def test_throw_404_if_publisher_not_found(self):
        response = self.client.get('/api/package/%s' % ('fake_publisher',))
        self.assertEqual(response.status_code, 404)

    def test_return_200_if_data_found(self):
        response = self.client.get('/api/package/%s' % (self.publisher,))
        data = json.loads(response.data)
        self.assertEqual(len(data['data']), 2)
        self.assertEqual(response.status_code, 200)

    def test_throw_500_if_db_not_set_up(self):
        with self.app.app_context():
            db.drop_all()
        response = self.client.get('/api/package/%s' % (self.publisher,))
        self.assertEqual(response.status_code, 500)

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()


class FinalizeMetaDataTestCase(unittest.TestCase):
    publisher = 'test_publisher'
    package = 'test_package'
    user_id = 1
    url = '/api/package/%s/%s/finalize' % (publisher, package)
    jwt_url = '/api/auth/token'

    def setUp(self):
        self.app = create_app()
        # self.app.app_context().push()
        self.client = self.app.test_client()
        with self.app.app_context():
            db.drop_all()
            db.create_all()
            self.user = User()
            self.user.id = self.user_id
            self.user.email, self.user.name, self.user.secret = \
                'test@test.com', self.publisher, 'super_secret'
            publisher = Publisher(name=self.publisher)
            association = PublisherUser(role=UserRoleEnum.owner)
            publisher.packages.append(MetaDataDB(name=self.package))
            association.publisher = publisher
            self.user.publishers.append(association)
            db.session.add(self.user)
            db.session.commit()
        response = self.client.post(self.jwt_url,
                                    data=json.dumps({
                                        'username': self.publisher,
                                        'secret': 'super_secret'
                                    }),
                                    content_type='application/json')
        data = json.loads(response.data)
        self.jwt = data['token']

    @patch('app.package.models.MetaDataDB.create_or_update')
    @patch('app.package.models.BitStore.get_metadata_body')
    @patch('app.package.models.BitStore.get_readme_object_key')
    @patch('app.package.models.BitStore.get_s3_object')
    def test_return_200_if_all_right(self, get_metadata_body, create_or_update,
                                     get_readme_object_key, get_s3_object):
        get_metadata_body.return_value = json.dumps(dict(name='package'))
        create_or_update.return_value = None
        get_readme_object_key.return_value = ''
        get_s3_object.return_value = ''
        auth = "bearer %s" % self.jwt
        response = self.client.post(self.url,
                                    data=json.dumps(dict()),
                                    headers=dict(Authorization=auth))
        self.assertEqual(200, response.status_code)

    def test_throw_403_if_user_not_exists_so_operation_not_permitted(self):
        with self.app.app_context():
            db.drop_all()
            db.create_all()
        auth = "bearer %s" % self.jwt
        response = self.client.post(self.url,
                                    data=json.dumps(dict()),
                                    headers=dict(Authorization=auth))
        self.assertEqual(403, response.status_code)

    @patch('app.package.models.BitStore.get_metadata_body')
    def test_throw_500_if_failed_to_get_data_from_s3(self, body_mock):
        body_mock.return_value = None
        auth = "bearer %s" % self.jwt
        response = self.client.post(self.url,
                                    data=json.dumps(dict()),
                                    headers=dict(Authorization=auth))
        self.assertEqual(500, response.status_code)

    def test_throw_403_if_user_not_permitted_for_this_operation(self):
        auth = "bearer %s" % self.jwt
        url = '/api/package/%s/%s/finalize' % ("test_publisher1", self.package)
        response = self.client.post(url,
                                    data=json.dumps(dict()),
                                    headers=dict(Authorization=auth))
        self.assertEqual(403, response.status_code)

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()


class SaveMetaDataTestCase(unittest.TestCase):
    publisher = 'test_publisher'
    package = 'test_package'
    user_id = 1
    url = '/api/package/%s/%s' % (publisher, package)
    jwt_url = '/api/auth/token'

    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()
        with self.app.app_context():
            db.drop_all()
            db.create_all()
            self.user = User()
            self.user.id = self.user_id
            self.user.email, self.user.name, self.user.secret = \
                'test@test.com', self.publisher, 'super_secret'
            self.pub = Publisher(name=self.publisher)
            association = PublisherUser(role=UserRoleEnum.owner)
            association.publisher = self.pub
            self.user.publishers.append(association)

            db.session.add(self.user)
            db.session.commit()
        response = self.client.post(self.jwt_url,
                                    data=json.dumps({
                                        'username': self.publisher,
                                        'secret': 'super_secret'
                                    }),
                                    content_type='application/json')
        data = json.loads(response.data)
        self.jwt = data['token']

    def test_should_throw_error_if_auth_header_missing(self):
        response = self.client.put(self.url)
        self.assertEqual(401, response.status_code)

    def test_should_throw_error_if_auth_header_not_starts_with_bearer(self):
        response = self.client.put(self.url,
                                   headers=dict(Authorization='auth 123'))
        self.assertEqual(401, response.status_code)

    def test_should_throw_error_if_auth_header_malformed(self):
        response = self.client.put(self.url,
                                   headers=dict(Authorization='bearer123'))
        self.assertEqual(401, response.status_code)

        response = self.client.put(self.url,
                                   headers=dict(Authorization='bearer 12 23'))
        self.assertEqual(401, response.status_code)

    @patch('app.package.models.BitStore.save_metadata')
    def test_return_200_if_all_right(self, save):
        save.return_value = None
        auth = "bearer %s" % self.jwt
        response = self.client.put(self.url,
                                   headers=dict(Authorization=auth),
                                   data=json.dumps({'name': 'package'}))
        self.assertEqual(200, response.status_code)

    @patch('app.package.models.BitStore.save_metadata')
    def test_return_403_if_user_not_matches_publisher(self, save):
        save.return_value = None
        auth = "bearer %s" % self.jwt
        response = self.client.put('/api/package/not-a-publisher/%s'%self.package,
                                   headers=dict(Authorization=auth),
                                   data=json.dumps({'name': 'package'}))
        self.assertEqual(403, response.status_code)

    @patch('app.package.models.BitStore.save_metadata')
    def test_return_403_if_user_not_found_so_not_permitted_this_action(self, save):
        with self.app.app_context():
            db.drop_all()
            db.create_all()
        save.return_value = None
        auth = "bearer %s" % self.jwt
        response = self.client.put(self.url,
                                   headers=dict(Authorization=auth),
                                   data=json.dumps({'name': 'package'}))

        self.assertEqual(403, response.status_code)

    @patch('app.package.models.BitStore.save_metadata')
    def test_return_500_for_internal_error(self, save):
        save.side_effect = Exception('some problem')
        auth = "bearer %s" % self.jwt
        response = self.client.put(self.url, headers=dict(Authorization=auth),
                                   data=json.dumps({'name': 'package'}))
        data = json.loads(response.data)
        self.assertEqual(500, response.status_code)
        self.assertEqual('GENERIC_ERROR', data['error_code'])

    @patch('app.package.models.BitStore.save_metadata')
    def test_throw_400_if_meta_data_is_invalid(self, save):
        save.return_value = None
        auth = "bearer %s" % self.jwt
        response = self.client.put(self.url, headers=dict(Authorization=auth),
                                   data=json.dumps({'name1': 'package'}))
        data = json.loads(response.data)
        self.assertEqual(400, response.status_code)
        self.assertEqual(data['error_code'], 'INVALID_DATA')
        # test metadata has no name
        response = self.client.put(self.url, headers=dict(Authorization=auth),
                                   data=json.dumps({'name': ''}))
        self.assertEqual(400, response.status_code)
        self.assertEqual(data['error_code'], 'INVALID_DATA')

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()


class DataProxyTestCase(unittest.TestCase):
    publisher = 'test_pub'
    package = 'test_package'
    resource = 'test_resource'
    url = '/api/package/dataproxy/{publisher}/{package}/r/{resource}.csv'\
        .format(publisher=publisher, package=package, resource=resource)

    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()

    @patch("app.package.models.BitStore.get_s3_object")
    @patch("app.package.models.BitStore.build_s3_key")
    def test_return_200_if_all_right_for_csv(self, build_key, get_s3_object):
        build_key.return_value = ''
        get_s3_object.return_value = 'test_header_0,test_header_1\n'\
                                     + 'test_value_0,test_value_3'
        response = self.client.get(self.url)
        data = response.data
        self.assertEqual(200, response.status_code)
        self.assertEqual(data, 'test_header_0,test_header_1\n'\
                                     + 'test_value_0,test_value_3\n')

    @patch("app.package.models.BitStore.get_s3_object")
    @patch("app.package.models.BitStore.build_s3_key")
    def test_return_200_if_all_right_for_json(self, build_key, get_s3_object):
        build_key.return_value = ''
        get_s3_object.return_value = 'test_header_0,test_header_1\n'\
                                     + 'test_value_0,test_value_1\n'\
                                     + 'test_value_2,test_value_3'
        self.url = self.url.split('.csv')[0] + '.json'
        response = self.client.get(self.url)
        data = response.data
        self.assertEqual(200, response.status_code)
        self.assertEqual(data, '['
                         + '{"test_header_0": "test_value_2", '
                         + '"test_header_1": "test_value_3"},'
                         + '{"test_header_0": "test_value_0", '
                         + '"test_header_1": "test_value_1"}'
                         + ']')

    @patch("app.package.models.BitStore.get_s3_object")
    @patch("app.package.models.BitStore.build_s3_key")
    def test_throw_500_if_not_able_to_get_data_from_s3(self,
                                                       build_key,
                                                       get_s3_object):
        build_key.return_value = ''
        get_s3_object.side_effect = Exception('failed')
        response = self.client.get(self.url)
        data = json.loads(response.data)
        self.assertEqual(500, response.status_code)
        self.assertEqual(data['message'], 'failed')


class EndToEndTestCase(unittest.TestCase):
    auth_token_url = '/api/auth/token'
    publisher = 'test_publisher'
    package = 'test_package'
    meta_data_url = '/api/package/%s/%s' % (publisher, package)
    bitstore_url = '/api/auth/bitstore_upload'
    finalize_url = '/api/package/%s/%s/finalize' % (publisher, package)
    test_data_package = {'name': 'test_package'}

    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()
        with self.app.app_context():
            db.drop_all()
            db.create_all()
            self.user = User()
            self.user.id = 1
            self.user.email, self.user.name, self.user.secret = \
                'test@test.com', self.publisher, 'super_secret'

            self.publisherObj = Publisher(name=self.publisher)

            association = PublisherUser(role=UserRoleEnum.owner)
            association.publisher = self.publisherObj
            self.user.publishers.append(association)

            db.session.add(self.user)
            db.session.commit()

    @patch('app.package.models.BitStore.get_readme_object_key')
    @patch('app.package.models.MetaDataDB.create_or_update')
    @patch('app.package.models.BitStore.get_metadata_body')
    @patch('app.package.models.BitStore.get_s3_object')
    @patch('app.package.models.BitStore.generate_pre_signed_put_obj_url')
    @patch('app.package.models.BitStore.save_metadata')
    def test_publish_end_to_end(self, save, signed_url, get_s3_object,
                                get_metadata_body, create_or_update,
                                get_readme_object_key):
        # Sending Username & Secret key
        rv = self.client.post(self.auth_token_url,
                              data=json.dumps({
                                  'username': 'test_publisher',
                                  'email': None,
                                  'secret': 'super_secret'
                              }),
                              content_type='application/json')
        # Testing Token received
        self.assertIn('token', rv.data)
        self.assertEqual(200, rv.status_code)

        # Sending recived token to server with Authentication Header
        token = json.loads(rv.data)['token']
        self.auth = "bearer %s" % token  # Saving token for future use
        save.return_value = None
        rv = self.client.put(self.meta_data_url, headers=dict(Authorization=self.auth),
                             data=json.dumps(self.test_data_package))
        # Testing Authentication status
        self.assertEqual({'status': 'OK'}, json.loads(rv.data))
        self.assertEqual(200, rv.status_code)

        # Adding to Meta Data
        descriptor = {'name': 'test description'}
        with self.app.app_context():
            p = Publisher.query.filter_by(name=self.publisher).one()
            metadata = MetaDataDB(name=self.package)
            p.packages.append(metadata)
            metadata.descriptor = json.dumps(descriptor)
            db.session.add(p)
            db.session.commit()
        rv = self.client.get('/api/package/%s' % (self.publisher,))
        data = json.loads(rv.data)
        # Testing Meta Data
        self.assertEqual(len(data['data']), 1)
        self.assertEqual(rv.status_code, 200)

        # Get S3 link for uploading Data file
        signed_url.return_value = 'https://trial_url'
        rv = self.client.post(self.bitstore_url,
                              data=json.dumps({
                                  'publisher': self.publisher,
                                  'package': self.package,
                                  'md5': ''
                              }),
                              content_type='application/json')
        # Testing S3 link
        self.assertEqual({'key': 'https://trial_url'}, json.loads(rv.data))
        self.assertEqual(200, rv.status_code)

        # Finalize
        get_metadata_body.return_value = json.dumps(dict(name='package'))
        create_or_update.return_value = None
        get_readme_object_key.return_value = ''
        get_s3_object.return_value = ''
        rv = self.client.post(self.finalize_url,
                              data=json.dumps(dict()),
                              headers=dict(Authorization=self.auth))
        # Test Data
        self.assertEqual(200, rv.status_code)

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()


class SoftDeleteTestCase(unittest.TestCase):
    publisher_name = 'test_publisher'
    package = 'test_package'
    url = "/api/package/{pub}/{pac}".format(pub=publisher_name,
                                            pac=package)
    user_id = 1
    jwt_url = '/api/auth/token'

    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()
        with self.app.app_context():
            db.drop_all()
            db.create_all()
            self.user = User()
            self.user.id = self.user_id
            self.user.email, self.user.name, self.user.secret = \
                'test@test.com', self.publisher_name, 'super_secret'

            self.publisher = Publisher(name=self.publisher_name)

            association = PublisherUser(role=UserRoleEnum.owner)
            association.publisher = self.publisher

            metadata = MetaDataDB(name=self.package)
            self.publisher.packages.append(metadata)
            self.user.publishers.append(association)

            db.session.add(self.user)
            db.session.commit()
        response = self.client.post(self.jwt_url,
                                    data=json.dumps({
                                        'username': self.publisher_name,
                                        'secret': 'super_secret'
                                    }),
                                    content_type='application/json')
        data = json.loads(response.data)
        self.jwt = data['token']
        self.auth = "bearer %s" % self.jwt

    @patch('app.package.models.BitStore.change_acl')
    @patch('app.package.models.MetaDataDB.change_status')
    def test_return_200_if_all_goes_well(self, change_status, change_acl):
        change_acl.return_value = True
        change_status.return_value = True

        response = self.client.delete(self.url, headers=dict(Authorization=self.auth))
        self.assertEqual(response.status_code, 200)

    @patch('app.package.models.BitStore.change_acl')
    @patch('app.package.models.MetaDataDB.change_status')
    def test_return_403_not_allowed_to_do_operation(self, change_status, change_acl):
        change_acl.return_value = True
        change_status.return_value = True

        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, 403)

    @patch('app.package.models.BitStore.change_acl')
    @patch('app.package.models.MetaDataDB.change_status')
    def test_throw_500_if_change_acl_fails(self,  change_status, change_acl):
        change_acl.return_value = False
        change_status.return_value = True
        response = self.client.delete(self.url, headers=dict(Authorization=self.auth))
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(data['message'], 'Failed to change acl')

    @patch('app.package.models.BitStore.change_acl')
    @patch('app.package.models.MetaDataDB.change_status')
    def test_throw_500_if_change_status_fails(self, change_status, change_acl):
        change_acl.return_value = True
        change_status.return_value = False
        response = self.client.delete(self.url, headers=dict(Authorization=self.auth))
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(data['message'], 'Failed to change status')

    @patch('app.package.models.BitStore.change_acl')
    @patch('app.package.models.MetaDataDB.change_status')
    def test_throw_generic_error_if_internal_error(self, change_status, change_acl):
        change_acl.side_effect = Exception('failed')
        change_status.return_value = False
        response = self.client.delete(self.url, headers=dict(Authorization=self.auth))
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(data['message'], 'failed')

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()


class HardDeleteTestCase(unittest.TestCase):
    publisher_name = 'test_publisher'
    package = 'test_package'
    url = "/api/package/{pub}/{pac}/purge".format(pub=publisher_name,
                                                  pac=package)
    user_id = 1
    user_id_member = 2
    user_member_name = 'test_user'
    jwt_url = '/api/auth/token'

    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()
        with self.app.app_context():
            db.drop_all()
            db.create_all()
            self.user = User()
            self.user.id = self.user_id
            self.user.email, self.user.name, self.user.secret = \
                'test@test.com', self.publisher_name, 'super_secret'

            self.user_member = User()
            self.user_member.id = self.user_id_member
            self.user_member.email, self.user_member.name, self.user_member.secret = \
                'test1@test.com', self.user_member_name, 'super_secret'

            self.publisher = Publisher(name=self.publisher_name)

            association = PublisherUser(role=UserRoleEnum.owner)
            association.publisher = self.publisher

            association1 = PublisherUser(role=UserRoleEnum.member)
            association1.publisher = self.publisher

            metadata = MetaDataDB(name=self.package)
            self.publisher.packages.append(metadata)
            self.user.publishers.append(association)
            self.user_member.publishers.append(association1)

            db.session.add(self.user)
            db.session.add(self.user_member)
            db.session.commit()
        response = self.client.post(self.jwt_url,
                                    data=json.dumps({
                                        'username': self.publisher_name,
                                        'secret': 'super_secret'
                                    }),
                                    content_type='application/json')
        data = json.loads(response.data)
        self.jwt = data['token']

        response = self.client.post(self.jwt_url,
                                    data=json.dumps({
                                       'username': self.user_member_name,
                                       'secret': 'super_secret'
                                   }),
                                   content_type='application/json')
        data = json.loads(response.data)
        self.jwt_member = data['token']

    @patch('app.package.models.BitStore.delete_data_package')
    @patch('app.package.models.MetaDataDB.delete_data_package')
    def test_return_200_if_all_goes_well(self, db_delete, bitstore_delete):
        bitstore_delete.return_value = True
        db_delete.return_value = True
        auth = "bearer %s" % self.jwt
        response = self.client.delete(self.url, headers=dict(Authorization=auth))
        self.assertEqual(response.status_code, 200)

    @patch('app.package.models.BitStore.delete_data_package')
    @patch('app.package.models.MetaDataDB.delete_data_package')
    def test_throw_500_if_change_acl_fails(self, db_delete, bitstore_delete):
        bitstore_delete.return_value = False
        db_delete.return_value = True
        auth = "bearer %s" % self.jwt
        response = self.client.delete(self.url, headers=dict(Authorization=auth))
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(data['message'], 'Failed to delete from s3')

    @patch('app.package.models.BitStore.delete_data_package')
    @patch('app.package.models.MetaDataDB.delete_data_package')
    def test_throw_500_if_change_status_fails(self, db_delete, bitstore_delete):
        bitstore_delete.return_value = True
        db_delete.return_value = False
        auth = "bearer %s" % self.jwt
        response = self.client.delete(self.url, headers=dict(Authorization=auth))
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(data['message'], 'Failed to delete from db')

    @patch('app.package.models.BitStore.delete_data_package')
    @patch('app.package.models.MetaDataDB.delete_data_package')
    def test_throw_generic_error_if_internal_error(self, db_delete, bitstore_delete):
        bitstore_delete.side_effect = Exception('failed')
        db_delete.return_value = False
        auth = "bearer %s" % self.jwt
        response = self.client.delete(self.url, headers=dict(Authorization=auth))
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(data['message'], 'failed')

    @patch('app.package.models.BitStore.delete_data_package')
    @patch('app.package.models.MetaDataDB.delete_data_package')
    def test_should_throw_403_if_user_is_not_owner_of_the_package(self,
                                                                  db_delete,
                                                                  bitstore_delete):
        bitstore_delete.return_value = True
        db_delete.return_value = True
        auth = "bearer %s" % self.jwt_member
        response = self.client.delete(self.url, headers=dict(Authorization=auth))
        self.assertEqual(response.status_code, 403)

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()


class TagDataPackageTestCase(unittest.TestCase):
    publisher_name = 'test_publisher'
    package = 'test_package'
    url = "/api/package/{pub}/{pac}/tag".format(pub=publisher_name,
                                                pac=package)
    user_id = 1
    user_not_allowed_id = 2
    user_not_allowed_name = 'other_publisher'
    user_member_id = 3
    user_member_name = 'member_publisher'
    jwt_url = '/api/auth/token'

    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()
        with self.app.app_context():
            self.bucket_name = self.app.config['S3_BUCKET_NAME']
            db.drop_all()
            db.create_all()
            self.user = User()
            self.user.id = self.user_id
            self.user.email, self.user.name, self.user.secret = \
                'test@test.com', self.publisher_name, 'super_secret'

            self.publisher = Publisher(name=self.publisher_name)

            association = PublisherUser(role=UserRoleEnum.owner)
            association.publisher = self.publisher

            metadata = MetaDataDB(name=self.package)
            self.publisher.packages.append(metadata)
            self.user.publishers.append(association)

            self.user_not_allowed = User()
            self.user_not_allowed.id = self.user_not_allowed_id
            self.user_not_allowed.email, self.user_not_allowed.name, \
                self.user_not_allowed.secret = \
                'test1@test.com', self.user_not_allowed_name, 'super_secret'

            self.publisher_not_allowed = Publisher(name=self.user_not_allowed_name)

            association_not_allowed = PublisherUser(role=UserRoleEnum.owner)
            association_not_allowed.publisher = self.publisher_not_allowed

            metadata = MetaDataDB(name=self.package)
            self.publisher_not_allowed.packages.append(metadata)
            self.user_not_allowed.publishers.append(association_not_allowed)

            self.user_member = User()
            self.user_member.id = self.user_member_id
            self.user_member.email, self.user_member.name, self.user_member.secret = \
                'tes2t@test.com', self.user_member_name, 'super_secret'

            association_member = PublisherUser(role=UserRoleEnum.member)
            association_member.publisher = self.publisher
            self.user_member.publishers.append(association_member)

            db.session.add(self.user)
            db.session.add(self.user_not_allowed)
            db.session.commit()
        response = self.client.post(self.jwt_url,
                                    data=json.dumps({
                                        'username': self.publisher_name,
                                        'secret': 'super_secret'
                                    }),
                                    content_type='application/json')
        data = json.loads(response.data)
        self.jwt = data['token']
        self.auth = "bearer %s" % self.jwt

    @patch('app.package.models.BitStore.copy_to_new_version')
    @patch('app.package.models.MetaDataDB.create_or_update_version')
    def test_return_200_if_all_goes_well(self, create_or_update_version, copy_to_new_version):
        copy_to_new_version.return_value = True
        create_or_update_version.return_value = True
        response = self.client.post(self.url,
                                    data=json.dumps({
                                        'version': 'tag_one'
                                    }),
                                    content_type='application/json',
                                    headers=dict(Authorization=self.auth))
        self.assertEqual(response.status_code, 200)

    @patch('app.package.models.BitStore.copy_to_new_version')
    @patch('app.package.models.MetaDataDB.create_or_update_version')
    def test_throw_400_if_version_missing(self, create_or_update_version, copy_to_new_version):
        copy_to_new_version.return_value = True
        create_or_update_version.return_value = True
        response = self.client.post(self.url,
                                    data=json.dumps({
                                        'version_fail': 'tag_one'
                                    }),
                                    content_type='application/json',
                                    headers=dict(Authorization=self.auth))
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual('ATTRIBUTE_MISSING', data['error_code'])

    @patch('app.package.models.BitStore.copy_to_new_version')
    @patch('app.package.models.MetaDataDB.create_or_update_version')
    def test_throw_500_if_failed_to_tag(self, create_or_update_version, copy_to_new_version):
        copy_to_new_version.return_value = False
        create_or_update_version.return_value = True
        response = self.client.post(self.url,
                                    data=json.dumps({
                                        'version': 'tag_one'
                                    }),
                                    content_type='application/json',
                                    headers=dict(Authorization=self.auth))
        self.assertEqual(response.status_code, 500)

    @mock_s3
    def test_throw_403_if_not_owner_or_member_of_publisher(self):
        s3 = boto3.client('s3')
        s3.create_bucket(Bucket=self.bucket_name)
        bit_store = BitStore('test_pub', 'test_package')
        read_me_key = bit_store.build_s3_key('test.md')
        data_key = bit_store.build_s3_key('data.csv')
        metadata_key = bit_store.build_s3_key('datapackage.json')
        s3.put_object(Bucket=self.bucket_name, Key=read_me_key, Body='readme')
        s3.put_object(Bucket=self.bucket_name, Key=data_key, Body='data')
        s3.put_object(Bucket=self.bucket_name, Key=metadata_key, Body='metedata')

        response = self.client.post(self.jwt_url,
                                    data=json.dumps({
                                        'username': self.user_not_allowed_name,
                                        'secret': 'super_secret'
                                    }),
                                    content_type='application/json')
        data = json.loads(response.data)
        jwt_not_allowed = data['token']
        auth_not_allowed = "bearer %s" % jwt_not_allowed

        response = self.client.post(self.url,
                                    data=json.dumps({
                                        'version': 'tag_one'
                                    }),
                                    content_type='application/json',
                                    headers=dict(Authorization=auth_not_allowed))
        self.assertEqual(response.status_code, 403)

        with self.app.app_context():
            data_latest = MetaDataDB.query.join(Publisher). \
                filter(Publisher.name == self.publisher_name,
                       MetaDataDB.name == self.package).all()
            self.assertEqual(1, len(data_latest))
        bit_store_tagged = BitStore('test_pub', 'test_package',
                                    'tag_one')
        objects_nu = s3.list_objects(Bucket=self.bucket_name,
                                     Prefix=bit_store_tagged
                                     .build_s3_versioned_prefix())
        self.assertTrue('Contents' not in objects_nu)

    @patch('app.package.models.BitStore.copy_to_new_version')
    @patch('app.package.models.MetaDataDB.create_or_update_version')
    def test_allow_if_member_of_publisher(self, create_or_update_version,
                                          copy_to_new_version):
        copy_to_new_version.return_value = False
        create_or_update_version.return_value = True
        response = self.client.post(self.jwt_url,
                                    data=json.dumps({
                                        'username': self.user_member_name,
                                        'secret': 'super_secret'
                                    }),
                                    content_type='application/json')
        data = json.loads(response.data)
        jwt_allowed = data['token']
        auth_allowed = "bearer %s" % jwt_allowed

        response = self.client.post(self.url,
                                    data=json.dumps({
                                        'version': 'tag_one'
                                    }),
                                    content_type='application/json',
                                    headers=dict(Authorization=auth_allowed))
        self.assertEqual(response.status_code, 500)

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()
