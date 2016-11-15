# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

from app import create_app
from flask import json
import unittest
from app.database import db
from app.mod_site.models import Catalog
from app.mod_api.models import User, MetaDataDB

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
            metadata = MetaDataDB(self.package, self.publisher)
            metadata.descriptor = json.dumps(descriptor)
            db.session.add(metadata)
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
            metadata = MetaDataDB(self.package, self.publisher)
            metadata.descriptor = json.dumps(descriptor)
            db.session.add(metadata)
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
            metadata = MetaDataDB(self.package, self.publisher)
            metadata.descriptor = json.dumps(descriptor)
            metadata.readme= readme
            db.session.add(metadata)
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
            metadata = MetaDataDB(self.package, self.publisher)
            metadata.descriptor = json.dumps(descriptor)
            db.session.add(metadata)
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
            metadata = MetaDataDB(self.package, self.publisher)
            metadata.descriptor = json.dumps(descriptor)
            db.session.add(metadata)
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
            metadata = MetaDataDB(self.package, self.publisher)
            metadata.descriptor = json.dumps(descriptor)
            db.session.add(metadata)
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
            metadata = MetaDataDB(self.package, self.publisher)
            metadata.descriptor = json.dumps(descriptor)
            db.session.add(metadata)
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
            metadata = MetaDataDB(self.package, self.publisher)
            metadata.descriptor = json.dumps(descriptor)
            db.session.add(metadata)
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
