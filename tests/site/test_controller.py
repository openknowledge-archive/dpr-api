# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

from flask.ext.oauthlib.client import OAuthResponse
from BeautifulSoup import BeautifulSoup
from app import create_app
from flask import json, template_rendered
from contextlib import nested, contextmanager
from mock import patch
import unittest
import os
from flask_testing import TestCase
from app.database import db
from app.package.models import Package, PackageTag
from app.profile.models import User, Publisher, UserRoleEnum


class WebsiteTestCase(unittest.TestCase):
    def setUp(self):
        self.publisher = 'demo'
        self.package = 'demo-package'
        self.app = create_app()
        self.client = self.app.test_client()
        with self.app.app_context():
            db.drop_all()
            db.create_all()

    def test_home_page(self):
        rv = self.client.get('/')
        self.assertNotEqual(404, rv.status_code)

    def test_home_shows_packages(self):
        descriptor = json.loads(open('fixtures/datapackage.json').read())
        with self.app.app_context():
            publisher = Publisher(name='core')
            metadata = Package(name='gold-prices')
            metadata.tags.append(PackageTag(descriptor=descriptor))
            publisher.packages.append(metadata)
            db.session.add(publisher)
            db.session.commit()
        rv = self.client.get('/')
        self.assertEqual(rv.status_code, 200)
        self.assertTrue('DEMO - CBOE Volatility Index' in rv.data)

    def test_logout_page(self):
        rv = self.client.get('/logout')
        self.assertNotEqual(404, rv.status_code)

    def test_publisher_page_loads_fine(self):
        with self.app.app_context():
            publisher = Publisher(name=self.publisher)
            db.session.add(publisher)
            db.session.commit()
        rv = self.client.get('/%s' % self.publisher)
        self.assertEqual(200, rv.status_code)

    def test_publisher_page_results_404_for_non_existing_publisher(self):
        with self.app.app_context():
            publisher = Publisher(name=self.publisher)
            db.session.add(publisher)
            db.session.commit()
        rv = self.client.get('/unknown' )
        self.assertEqual(404, rv.status_code)

    def test_data_package_page(self):
        descriptor = json.loads(open('fixtures/datapackage.json').read())
        with self.app.app_context():
            publisher = Publisher(name=self.publisher)
            metadata = Package(name=self.package)
            metadata.tags.append(PackageTag(descriptor=descriptor))
            publisher.packages.append(metadata)
            db.session.add(publisher)
            db.session.commit()
        rv = self.client.get('/{publisher}/{package}'.\
                             format(publisher=self.publisher,
                                    package=self.package))
        self.assertNotEqual(404, rv.status_code)
        self.assertIn('DOWNLOAD FILES', rv.data.decode("utf8"))

        rv = self.client.get('/non-existing/demo-package')
        self.assertEqual(404, rv.status_code)


    def test_data_package_page_loads_if_descriptor_has_bad_licenses(self):
        descriptor = json.loads(open('fixtures/datapackage.json').read())
        descriptor['licenses'] = {'url': 'test/url', 'type': 'Test'}
        with self.app.app_context():
            publisher = Publisher(name=self.publisher)
            metadata = Package(name=self.package)
            metadata.tags.append(PackageTag(descriptor=descriptor))
            publisher.packages.append(metadata)
            db.session.add(publisher)
            db.session.commit()
        rv = self.client.get('/%s/%s' %(self.publisher,self.package))
        self.assertEqual(200, rv.status_code)


    def test_data_package_page_load_without_views(self):
        descriptor = {"data": [], "resources": []}
        with self.app.app_context():
            publisher = Publisher(name=self.publisher)
            metadata = Package(name=self.package)
            metadata.tags.append(PackageTag(descriptor=descriptor))
            publisher.packages.append(metadata)
            db.session.add(publisher)
            db.session.commit()
        rv = self.client.get('/{publisher}/{package}'.\
                             format(publisher=self.publisher,
                                    package=self.package))
        self.assertNotEqual(404, rv.status_code)
        self.assertIn('DOWNLOAD FILES', rv.data.decode("utf8"))

        rv = self.client.get('/non-existing/demo-package')
        self.assertEqual(404, rv.status_code)

    def test_api_docs(self):
        rv = self.client.get(self.app.config['API_DOCS'])
        self.assertEqual(200, rv.status_code)
        assert 'swagger' in rv.data

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()


class SignupEndToEndTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()
        self.signup_url_for_auth0 = "api/auth/login"
        self.oAuth_callback = 'api/auth/callback?code=xyz'
        self.env_variables = {
            'AUTH0_DOMAIN': 'test_auth0_domain_xyz',
            'AUTH0_CLIENT_ID': 'test_client_id_xyz',
            'SERVER_NAME': 'server',
        }
        self.auth0_url = "https://test_auth0_domain_xyz/login?client=test_client_id_xyz"

        # OAuth User info
        self.oAuth_user_info = {
            'name': 'The Big User',
            'login': 'test_username_xyz',
            'email': 'test@mail.com'
        }

        with self.app.app_context():
            db.drop_all()
            db.create_all()

    @contextmanager
    def captured_templates(self, app):
        recorded = []

        def record(sender, template, context, **extra):
            recorded.append((template, context))

        template_rendered.connect(record, app)
        try:
            yield recorded
        finally:
            template_rendered.disconnect(record, app)

    def test_end_to_end(self):
        # Loading Home
        rv = self.client.get('/')
        self.assertNotIn('404', rv.data.decode("utf8"))

        with nested(patch("flask_oauthlib.client.OAuthRemoteApp.authorized_response"),
                    patch('flask_oauthlib.client.OAuthRemoteApp.get'),
                    patch('app.auth.jwt')) \
                as (get_auth0_token, get_user, JWTHelper):
            # Mocking Auth0 user info & Return value for Dashboard
            with self.app.app_context():
                get_user.return_value = OAuthResponse(resp=None,
                                                      content=json.dumps(self.oAuth_user_info),
                                                      content_type='application/json')

                # Testing with Captured Templates
                with self.captured_templates(self.app) as templates:
                    rv = self.client.get(self.oAuth_callback)
                    template, context = templates[0]
                    user_created = User.query.filter_by(email=self.oAuth_user_info['email'])

                    # Check new user created
                    self.assertEqual(user_created.count(), 1)
                    new_user = user_created[0]
                    # Verify the Secret Code Generated
                    self.assertIsNotNone(new_user.secret)

                    # Verify Publishers Association
                    self.assertEqual(len(new_user.publishers), 1)

                    # Verify  Owner Association
                    self.assertEqual(new_user.publishers[0].role, UserRoleEnum.owner)

                    # Checking template rendered
                    self.assertEqual('dashboard.html', template.name)

                    # Checking User Object passed with context
                    self.assertEqual(self.oAuth_user_info[
                                         'login'], context['current_user'].name)

                    # Dashboad loaded with status code 200
                    self.assertEqual(rv.status_code, 200)

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()


class ContextProcessorTestCase(TestCase):
    def create_app(self):
        os.putenv('STAGE', '')
        return create_app()


class DataPackageShowTest(unittest.TestCase):

    def setUp(self):
        self.publisher = 'demo'
        self.package = 'demo-package'
        self.app = create_app()
        self.client = self.app.test_client()
        with self.app.app_context():
            db.drop_all()
            db.create_all()
            descriptor = json.loads(open('fixtures/datapackage.json').read())
            readme = open('fixtures/README.md').read()
            publisher = Publisher(name=self.publisher)
            metadata = Package(name=self.package)
            metadata.tags.append(PackageTag(descriptor=descriptor, readme=readme))

            publisher.packages.append(metadata)
            db.session.add(publisher)
            db.session.commit()

    def test_short_read_plain_text(self):
        response = self.client.get('/demo/demo-package')
        soap = BeautifulSoup(response.data.decode("utf8"))
        description = soap.findAll("div", {"class": "description"})

        self.assertFalse(description[0].__contains__('##'))
        self.assertFalse(description[0].__contains__('###'))

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()
