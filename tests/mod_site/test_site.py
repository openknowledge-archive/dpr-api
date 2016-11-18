# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

from app import create_app
from flask import json, template_rendered
from contextlib import nested, contextmanager
from mock import patch
import re
import unittest
from app.database import db
from app.mod_site.models import Catalog
from app.mod_api.models import User, MetaDataDB, Publisher

class CatalogTestCase(unittest.TestCase):
    def setUp(self):
        self.publisher = 'demo'
        self.package = 'demo-package'
        self.app = create_app()
        self.client = self.app.test_client()

    def test_construct_dataset(self):
        descriptor = json.loads(open('fixtures/datapackage.json').read())
        with self.app.app_context():
            db.drop_all()
            db.create_all()
            publisher = Publisher(name=self.publisher)
            metadata = MetaDataDB(name=self.package)
            metadata.descriptor = json.dumps(descriptor)
            publisher.packages.append(metadata)
            db.session.add(publisher)
            db.session.commit()
        response = self.client.get('/api/package/%s/%s'%\
                                   (self.publisher, self.package))    
        catalog = Catalog(json.loads(response.data))
        dataset = catalog.construct_dataset()
        self.assertEqual(dataset.get('name'), descriptor.get('name'))
        self.assertIn('localurl', dataset.get('resources')[0])
        self.assertNotEqual(len(dataset.get('views')), 0)

    def test_adds_local_urls(self):
        descriptor = {
            'name': 'test',
            'resources': [{'name': 'first'},{'name': 'second'}]
        }
        with self.app.app_context():
            db.drop_all()
            db.create_all()
            publisher = Publisher(name=self.publisher)
            metadata = MetaDataDB(name=self.package)
            metadata.descriptor = json.dumps(descriptor)
            publisher.packages.append(metadata)
            db.session.add(publisher)
            db.session.commit()
        response = self.client.get('/api/package/%s/%s'%\
                                   (self.publisher, self.package))    
        catalog = Catalog(json.loads(response.data))
        dataset = catalog.construct_dataset('http://example.com/')
        self.assertEqual(dataset.\
                         get('resources')[0].get('localurl'),
        'http://example.com/api/dataproxy/demo/demo-package/r/first.csv')
        self.assertEqual(dataset.\
                         get('resources')[1].get('localurl'),
        'http://example.com/api/dataproxy/demo/demo-package/r/second.csv')

    def test_adds_readme_if_there_is(self):
        descriptor = {
            'name': 'test',
            'resources': []
        }
        readme = 'README'
        with self.app.app_context():
            db.drop_all()
            db.create_all()
            publisher = Publisher(name=self.publisher)
            metadata = MetaDataDB(name=self.package)
            metadata.descriptor = json.dumps(descriptor)
            metadata.readme = readme
            publisher.packages.append(metadata)
            db.session.add(publisher)
            db.session.commit()
        response = self.client.get('/api/package/%s/%s'%\
                                   (self.publisher, self.package))    
        catalog = Catalog(json.loads(response.data))
        dataset = catalog.construct_dataset()
        self.assertEqual(dataset.get('readme'), 'README')

    def test_adds_empty_readme_if_there_is_not(self):
        descriptor = {
            'name': 'test',
            'resources': []
        }
        with self.app.app_context():
            db.drop_all()
            db.create_all()
            publisher = Publisher(name=self.publisher)
            metadata = MetaDataDB(name=self.package)
            metadata.descriptor = json.dumps(descriptor)
            publisher.packages.append(metadata)
            db.session.add(publisher)
            db.session.commit()
        response = self.client.get('/api/package/%s/%s'%\
                                   (self.publisher, self.package))    
        catalog = Catalog(json.loads(response.data))
        dataset = catalog.construct_dataset()
        self.assertEqual(dataset.get('readme'), '')

    def test_get_views(self):
        descriptor = {
            'name': 'test',
            'resources': [],
            'views': [{"type": "graph"}]
        }
        with self.app.app_context():
            db.drop_all()
            db.create_all()
            publisher = Publisher(name=self.publisher)
            metadata = MetaDataDB(name=self.package)
            metadata.descriptor = json.dumps(descriptor)
            publisher.packages.append(metadata)
            db.session.add(publisher)
            db.session.commit()
        response = self.client.get('/api/package/%s/%s'%\
                                   (self.publisher, self.package))    
        catalog = Catalog(json.loads(response.data))
        views = catalog.get_views()
        self.assertNotEqual(len(views), 0)
        self.assertEqual(views[0].get('type'), 'graph')
        
    def test_get_views_if_views_dont_exist(self):
        descriptor = {
            'name': 'test',
            'resources': []
        }
        with self.app.app_context():
            db.drop_all()
            db.create_all()
            publisher = Publisher(name=self.publisher)
            metadata = MetaDataDB(name=self.package)
            metadata.descriptor = json.dumps(descriptor)
            publisher.packages.append(metadata)
            db.session.add(publisher)
            db.session.commit()
        response = self.client.get('/api/package/%s/%s'%\
                                   (self.publisher, self.package))    
        catalog = Catalog(json.loads(response.data))
        views = catalog.get_views()
        self.assertEqual(views, [])

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
        self.assertNotIn('404', rv.data.decode("utf8"))

    def test_logout_page(self):
        rv = self.client.get('/logout')
        self.assertNotIn('404', rv.data)

    def test_data_package_page(self):
        descriptor = json.loads(open('fixtures/datapackage.json').read())
        with self.app.app_context():
            publisher = Publisher(name=self.publisher)
            metadata = MetaDataDB(name=self.package)
            metadata.descriptor = json.dumps(descriptor)
            publisher.packages.append(metadata)
            db.session.add(publisher)
            db.session.commit()
        rv = self.client.get('/{publisher}/{package}'.\
                             format(publisher=self.publisher,
                                    package=self.package))
        self.assertNotIn('404', rv.data.decode("utf8"))
        self.assertIn('Data Files', rv.data.decode("utf8"))
        # cheks handsontable load
        self.assertIn('handsontable', rv.data.decode("utf8"))
        # cheks Vega graph load
        self.assertIn('vega', rv.data.decode("utf8"))

        rv = self.client.get('/non-existing/demo-package')
        self.assertIn('404', rv.data)
        # cheks handsontable not loaded
        self.assertNotIn('handsontable', rv.data)
        # cheks graph not loaded
        self.assertNotIn('vega', rv.data)

    def test_data_package_page_load_without_views(self):
        descriptor = {"data": [], "resources": []}
        with self.app.app_context():
            publisher = Publisher(name=self.publisher)
            metadata = MetaDataDB(name=self.package)
            metadata.descriptor = json.dumps(descriptor)
            publisher.packages.append(metadata)
            db.session.add(publisher)
            db.session.commit()
        rv = self.client.get('/{publisher}/{package}'.\
                             format(publisher=self.publisher,
                                    package=self.package))
        self.assertNotIn('404', rv.data.decode("utf8"))
        self.assertIn('Data Files', rv.data.decode("utf8"))
        # cheks handsontable load
        self.assertIn('handsontable', rv.data.decode("utf8"))
        # cheks Vega graph load
        self.assertIn('vega', rv.data.decode("utf8"))


        rv = self.client.get('/non-existing/demo-package')
        self.assertIn('404', rv.data)
        # cheks handsontable not loaded
        self.assertNotIn('handsontable', rv.data)
        # cheks graph not loaded
        self.assertNotIn('vega', rv.data)

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

class SignupEndToEndTestCase(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()
        self.signup_url_for_auth0 = "api/auth/login"
        self.auth0_callback = 'api/auth/callback?code=xyz'
        self.env_variables = {
            'AUTH0_DOMAIN': 'test_auth0_domain_xyz',
            'AUTH0_CLIENT_ID': 'test_client_id_xyz',
            'SERVER_NAME': 'server',
        }
        self.auth0_url = "https://test_auth0_domain_xyz/login?client=test_client_id_xyz"

        # Auth0 Callback info
        self.auth0_user_info = {
            'user_id': 'new_test_id',
            'username': 'test_username_xyz',
            'email': 'test@mail.com'
        }

        with self.app.app_context():
            db.drop_all()
            db.create_all()
            # Mocked to DB
            #self.user = User()
            #self.user.user_id = self.auth0_user_info['user_id']
            #self.user.email = self.auth0_user_info['email']
            #self.user.name = self.auth0_user_info['username']
            # db.session.add(self.user)
            # db.session.commit()

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

        # Sign Up button
        self.assertIn('Sign Up', rv.data.decode("utf8"))

        search_signup_url = re.search(
            'href="(.*?)".*Sign Up', rv.data.decode("utf8"))
        signup_up_url = search_signup_url.groups()[0]

        # Click Signup Button & Mocking Auth0 Parameter for SignUp
        with patch.dict(self.app.config, self.env_variables):
            rv = self.client.get(signup_up_url)
            self.assertIn(self.auth0_url, rv.data.decode("utf8"))

            # Checking Redirect to Auth0 Url
            self.assertEqual(rv.status_code, 302)

        with nested(patch('app.mod_api.controllers.get_user_info_with_code'),
                    patch('app.mod_api.controllers.JWTHelper'),
                    patch('app.mod_api.models.User.create_or_update_user_from_callback')) \
                as (get_user_with_code, JWTHelper, create_user):

            # Mocking Auth0 user info & Return value for Dashboard
            get_user_with_code('xyz').side_effect = self.auth0_user_info

            with self.captured_templates(self.app) as templates:
                rv = self.client.get(self.auth0_callback)
                # Call to Crete or Update DB
                self.assertEqual(create_user.call_count, 1)
                template, context = templates[0]
                # Checking template rendered
                self.assertEqual('dashboard.html', template.name)
                # Token sent along with context
                self.assertIn('encoded_token', context)
                # Dashboad loaded with status code 200
                self.assertEqual(rv.status_code, 200)

        # Actions on DB
        with self.app.app_context():
            # Call to create the DB
            user = User.create_or_update_user_from_callback(
                self.auth0_user_info)

            # Verifying Returned User from Create User or Update
            self.assertEqual(user.name, self.auth0_user_info['username'])

            # Get user from DB
            user_in_db = User.query.filter_by(
                name=self.auth0_user_info['username']).one()

            # Verifying Data in DB
            self.assertEqual(user_in_db.name, self.auth0_user_info['username'])
            # Verify the Secret Code Generated
            self.assertIsNotNone(user_in_db.secret)
            # Verify Publishers Association
            self.assertEqual(len(user_in_db.publishers), 1)
            # Verify  Owner Association
            self.assertEqual(user_in_db.publishers[0].role, 'OWNER')

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
