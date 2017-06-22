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

    def test_return_200_if_email_and_secret_matches(self):
        rv = self.client.post(self.auth_token_url,
                              data=json.dumps({
                                  'username': None,
                                  'email': 'test@test.com',
                                  'secret': 'super_secret'
                              }),
                              content_type='application/json')
        self.assertEqual(rv.status_code, 200)

    def test_throw_400_if_user_name_and_email_is_none(self):
        rv = self.client.post(self.auth_token_url,
                              data=json.dumps({
                                  'secret': 'abc',
                                  'username': 'test@test.com'
                              }),
                              content_type='application/json')
        data = json.loads(rv.data)
        assert rv.status_code == 403
        assert data['message'] == 'Invalid secret for user'


class CallbackHandlingTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()

    @patch('flask_oauthlib.client.OAuthRemoteApp.authorized_response')
    def test_throw_500_if_error_getting_user_info_from_oauth(self, authorized_response):
        authorized_response.return_value = {'name': 'bond','access_token': 'token'}

        response = self.client.get('/api/auth/callback?code=123')

        data = json.loads(response.data)

        print (data)

        self.assertEqual(data['message'], 'Internal Server Error')
        self.assertEqual(response.status_code, 500)

    @patch('flask_oauthlib.client.OAuthRemoteApp.authorized_response')
    @patch('flask_oauthlib.client.OAuthRemoteApp.get')
    def test_throw_404_if_email_not_found(self, get_user,authorized_response):
        authorized_response.return_value = {'access_token': 'token'}
        get_user.side_effect = lambda k:{
            'user': OAuthResponse(
                resp=None,
                content=json.dumps(dict()),
                content_type='application/json'
            ),
            'user/emails': OAuthResponse(
                resp=None,
                content=json.dumps([]),
                content_type='application/json')
        }.get(k, 'unhandled request %s'%k)
        response = self.client.get('/api/auth/callback?code=123')
        data = json.loads(response.data)
        self.assertEqual(data['message'], 'Email Not Found')
        self.assertEqual(response.status_code, 404)

    @patch('flask_oauthlib.client.OAuthRemoteApp.authorized_response')
    def test_throw_400_access_denied_if_authorized_response_is_none(self, authorized_response):
        authorized_response.return_value = None
        response = self.client.get('/api/auth/callback?code=123')

        data = json.loads(response.data)

        self.assertEqual(data['message'], 'Access Denied')
        self.assertEqual(response.status_code, 400)

    @patch('flask_oauthlib.client.OAuthRemoteApp.authorized_response')
    @patch('flask_oauthlib.client.OAuthRemoteApp.get')
    @patch('app.auth.jwt.JWT.encode')
    @patch('app.logic.User.find_or_create')
    def test_gets_private_email_and_return_200_if_all_right(self,
                                     create_user, jwt_helper, get_user,
                                     authorized_response):
        authorized_response.return_value = {'access_token': 'token'}
        get_user.side_effect = lambda k:{
            'user': OAuthResponse(
                resp=None,
                content=json.dumps(dict()),
                content_type='application/json'
            ),
            'user/emails': OAuthResponse(
                resp=None,
                content=json.dumps([{
                            "email": "user@dpr.com",
                            "verified": True,
                            "primary": True
                          }]),
                content_type='application/json')
        }.get(k, 'unhandled request %s'%k)
        jwt_helper.return_value = "132432"
        create_user.return_value = User(id=1, email="user@dpr.com", name='abc', secret='12345')
        response = self.client.get('/api/auth/callback?code=123')
        self.assertEqual(create_user.call_count, 1)
        self.assertEqual(jwt_helper.call_count, 1)
        self.assertEqual(response.status_code, 200)

    @patch('flask_oauthlib.client.OAuthRemoteApp.authorized_response')
    @patch('flask_oauthlib.client.OAuthRemoteApp.get')
    @patch('app.auth.jwt.JWT.encode')
    @patch('app.logic.User.find_or_create')
    def test_return_200_if_all_right(self,
                                     create_user, jwt_helper, get_user,
                                     authorized_response):
        authorized_response.return_value = {'access_token': 'token'}
        get_user.return_value = OAuthResponse(resp=None,
                                              content=json.dumps(dict({'email': 'user@dpr.com'})),
                                              content_type='application/json')
        jwt_helper.return_value = "132432"
        create_user.return_value = User(id=1, email="user@dpr.com", name='abc', secret='12345')
        response = self.client.get('/api/auth/callback?code=123')
        self.assertEqual(create_user.call_count, 1)
        self.assertEqual(jwt_helper.call_count, 1)
        self.assertEqual(response.status_code, 200)


    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()


import tests.base as base

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
            base.make_fixtures(self.app, self.package, self.publisher, self.user_id)
            self.jwt = base.get_valid_token(self.publisher)
            self.jwt1 = base.get_valid_token('test1')

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

