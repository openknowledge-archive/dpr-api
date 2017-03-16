# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import unittest
import json

from flask.ext.oauthlib.client import OAuthResponse
from mock import patch
from app import create_app
from app.database import db
from moto import mock_s3
from app.profile.models import User, Publisher, PublisherUser, UserRoleEnum
from app.package.models import Package


class AuthTokenTestCase(unittest.TestCase):
    auth_token_url = '/api/auth/token'

    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()
        with self.app.app_context():
            db.drop_all()
            db.create_all()
            self.user = User()
            self.user.user_id = 'trial_id'
            self.user.email, self.user.name, self.user.secret = \
                'test@test.com', 'test_user', 'super_secret'
            db.session.add(self.user)
            db.session.commit()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()

    def test_throw_400_if_user_name_and_email_is_none(self):
        rv = self.client.post(self.auth_token_url,
                              data=json.dumps({
                                  'username': None,
                                  'email': None
                              }),
                              content_type='application/json')
        data = json.loads(rv.data)
        assert rv.status_code == 400
        assert data['error_code'] == 'INVALID_INPUT'

    def test_throw_400_if_secret_is_none(self):
        rv = self.client.post(self.auth_token_url,
                              data=json.dumps({
                                  'username': 'test',
                                  'secret': None,
                              }),
                              content_type='application/json')
        assert rv.status_code == 400
        data = json.loads(rv.data)
        assert data['error_code'] == 'INVALID_INPUT'

    def test_throw_404_if_user_id_do_not_exists(self):
        rv = self.client.post(self.auth_token_url,
                              data=json.dumps({
                                  'username': None,
                                  'email': 'test1@test.com',
                                  'secret': 'super_secret'
                              }),
                              content_type='application/json')
        data = json.loads(rv.data)
        self.assertEqual(rv.status_code, 404)
        self.assertEqual(data['error_code'], 'USER_NOT_FOUND')

    def test_throw_404_if_user_email_do_not_exists(self):
        rv = self.client.post(self.auth_token_url,
                              data=json.dumps({
                                  'username': 'not_found_user',
                                  'email': None,
                                  'secret': 'super_secret'
                              }),
                              content_type='application/json')
        data = json.loads(rv.data)
        self.assertEqual(rv.status_code, 404)
        self.assertEqual(data['error_code'], 'USER_NOT_FOUND')

    def test_throw_403_if_user_name_and_secret_key_does_not_match(self):
        rv = self.client.post(self.auth_token_url,
                              data=json.dumps({
                                  'username': 'test_user',
                                  'email': None,
                                  'secret': 'super_secret1'
                              }),
                              content_type='application/json')
        data = json.loads(rv.data)
        self.assertEqual(rv.status_code, 403)
        self.assertEqual(data['error_code'], 'SECRET_ERROR')

    def test_throw_403_if_email_and_secret_key_does_not_match(self):
        rv = self.client.post(self.auth_token_url,
                              data=json.dumps({
                                  'username': None,
                                  'email': 'test@test.com',
                                  'secret': 'super_secret1'
                              }),
                              content_type='application/json')
        data = json.loads(rv.data)
        self.assertEqual(rv.status_code, 403)
        self.assertEqual(data['error_code'], 'SECRET_ERROR')

    def test_throw_500_if_exception_occours(self):
        rv = self.client.post(self.auth_token_url,
                              data="'username': None,",
                              content_type='application/json')
        data = json.loads(rv.data)
        self.assertEqual(rv.status_code, 500)
        self.assertEqual(data['error_code'], 'GENERIC_ERROR')

    def test_return_200_if_email_and_secret_matches(self):
        rv = self.client.post(self.auth_token_url,
                              data=json.dumps({
                                  'username': None,
                                  'email': 'test@test.com',
                                  'secret': 'super_secret'
                              }),
                              content_type='application/json')
        self.assertEqual(rv.status_code, 200)

    def test_return_200_if_user_id_and_secret_matches(self):
        rv = self.client.post(self.auth_token_url,
                              data=json.dumps({
                                  'username': 'test_user',
                                  'email': None,
                                  'secret': 'super_secret'
                              }),
                              content_type='application/json')
        self.assertEqual(rv.status_code, 200)


class CallbackHandlingTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()

    @patch('flask_oauthlib.client.OAuthRemoteApp.authorized_response')
    def test_throw_500_if_error_getting_user_info_from_oauth(self, authorized_response):
        authorized_response.return_value = {'name': 'bond'}

        response = self.client.get('/api/auth/callback?code=123')

        data = json.loads(response.data)

        self.assertEqual(data['error_code'], 'GENERIC_ERROR')
        self.assertEqual(response.status_code, 500)

    @patch('flask_oauthlib.client.OAuthRemoteApp.authorized_response')
    @patch('flask_oauthlib.client.OAuthRemoteApp.get')
    @patch('app.auth.models.JWT.encode')
    @patch('app.profile.models.User.create_or_update_user_from_callback')
    def test_return_200_if_all_right(self,
                                     create_user, jwt_helper, get_user,
                                     authorized_response):
        authorized_response.return_value = {'access_token': 'token'}
        get_user.return_value = OAuthResponse(resp=None,
                                              content=json.dumps(dict()),
                                              content_type='application/json')
        jwt_helper.return_value = "132432"
        create_user.return_value = User(id=1, email="abc@abc.com", name='abc', secret='12345')
        response = self.client.get('/api/auth/callback?code=123')
        self.assertEqual(create_user.call_count, 1)
        self.assertEqual(jwt_helper.call_count, 1)
        self.assertEqual(response.status_code, 200)

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()


class AuthorizeUploadTestCase(unittest.TestCase):
    publisher = 'test_publisher'
    package = 'test_package'
    user_id = 1
    url = '/api/datastore/authorize'
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
            self.pub.packages.append(Package(name=self.package))
            association = PublisherUser(role=UserRoleEnum.owner)
            association.publisher = self.pub
            self.user.publishers.append(association)

            user1 = User(id=2, name='test1',
                         secret='super_secret1', email="test1@test.com")
            pub1 = Publisher(name='test1')
            association1 = PublisherUser(role=UserRoleEnum.owner)
            association1.publisher = pub1
            user1.publishers.append(association1)

            db.session.add(self.user)
            db.session.add(user1)
            db.session.commit()
        response = self.client.post(self.jwt_url,
                                    data=json.dumps({
                                        'username': self.publisher,
                                        'secret': 'super_secret'
                                    }),
                                    content_type='application/json')
        data = json.loads(response.data)
        self.jwt = data['token']

        response = self.client.post(self.jwt_url,
                                    data=json.dumps({
                                        'username': 'test1',
                                        'secret': 'super_secret1'
                                    }),
                                    content_type='application/json')
        data = json.loads(response.data)
        self.jwt1 = data['token']

    @mock_s3
    def test_should_return_200_if_all_right(self):
        auth = "%s" % self.jwt
        data = {
            'metadata': {
                "owner": self.publisher,
                "name": self.package
            },
            "filedata": {
                "package.json": {
                    "name": "package.json",
                    "md5": "12345y65uyhgfed23243y6"
                }
            }
        }
        response = self.client.post(self.url,
                                    headers={'Auth-Token': auth},
                                    data=json.dumps(data),
                                    content_type='application/json')
        self.assertEqual(200, response.status_code)

    @mock_s3
    def test_should_return_500_if_data_not_present(self):
        auth = "%s" % self.jwt
        data = {
            'metadata': {
                "owner": self.publisher,
                "name": self.package
            },
            "filedata": {
                "package.json": {
                    "name": "package.json"
                }
            }
        }
        response = self.client.post(self.url,
                                    headers={'Auth-Token': auth},
                                    data=json.dumps(data),
                                    content_type='application/json')
        self.assertEqual(500, response.status_code)

    @mock_s3
    def test_should_return_400_if_unauthorized(self):
        auth = "%s" % self.jwt1
        data = {
            'metadata': {
                "owner": self.publisher,
                "name": self.package
            },
            "filedata": {
                "package.json": {
                    "name": "package.json"
                }
            }
        }
        response = self.client.post(self.url,
                                    headers={'Auth-Token': auth},
                                    data=json.dumps(data),
                                    content_type='application/json')
        self.assertEqual(400, response.status_code)

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()
