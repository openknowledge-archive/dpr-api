from app import create_app
from flask import json
import unittest
from app.database import db
from app.mod_site.models import Catalog
from app.mod_api.models import User, MetaDataDB

class CatalogTestCase(unittest.TestCase):
    def setUp(self):
        self.publisher = 'demo'
        self.package = 'finance-vix'
        self.app = create_app()

    def test_load(self):
        datapackage = json.loads(open('fixtures/datapackage.json').read())
        datapackage['owner'] = self.publisher
        catalog = Catalog()
        catalog.load([datapackage])

        self.assertIn('demo',catalog._cache)
        self.assertIn(self.package, catalog._cache[self.publisher] )
        self.assertEqual(catalog._cache[self.publisher][self.package], datapackage)
    
    def test_get(self):
        datapackage = json.loads(open('fixtures/datapackage.json').read())
        datapackage['owner'] = self.publisher
        catalog = Catalog()
        catalog.load([datapackage])
        result = catalog.get(self.publisher, self.package)
        self.assertEqual(result, datapackage)
        # test unknown owner
        result = catalog.get('anon', self.package)
        self.assertIsNone(result)
        
    def test_query(self):
        datapackage = json.loads(open('fixtures/datapackage.json').read())
        datapackage['owner'] = self.publisher
        catalog = Catalog()
        catalog.load([datapackage])
        
        self.assertEqual(catalog.query(), [datapackage])

    def test_by_owner(self):
        datapackage = json.loads(open('fixtures/datapackage.json').read())
        datapackage['owner'] = self.publisher
        catalog = Catalog()
        catalog.load([datapackage])
        
        self.assertEqual(catalog.by_owner(self.publisher), [datapackage])
        self.assertEqual(catalog.by_owner('anon'), [])

class WebsiteTestCase(unittest.TestCase):
    def setUp(self):
        self.publisher = 'demo'
        self.package = 'finance-vix'
        self.app = create_app()
        self.client = self.app.test_client()
        with self.app.app_context():
            db.drop_all()
            db.create_all()
    
    def test_home_page(self):
        rv = self.client.get('/')
        self.assertNotIn('404', rv.data)

    def test_logout_page(self):
        rv = self.client.get('/logout')
        self.assertNotIn('404', rv.data)

    def test_data_package_page(self):
        descriptor=json.loads(open('fixtures/datapackage.json').read())
        with self.app.app_context():
            metadata = MetaDataDB(self.package, self.publisher)
            metadata.descriptor = json.dumps(descriptor)
            db.session.add(metadata)
            db.session.commit()
        rv = self.client.get('/{publisher}/{package}'.format(publisher=self.publisher, package=self.package))
        self.assertNotIn('404', rv.data)
        self.assertIn('Data Files', rv.data)
        self.assertIn('handsontable', rv.data) # cheks handsontable load
        self.assertIn('vega', rv.data) # cheks Vega graph load


        rv = self.client.get('/non-existing/demo-package')
        self.assertIn('404', rv.data)
        self.assertNotIn('handsontable', rv.data) # cheks handsontable not loaded
        self.assertNotIn('vega', rv.data) # cheks graph not loaded

    def test_data_package_page_load_without_views(self):
        descriptor={"data": [], "resources": []}
        with self.app.app_context():
            metadata = MetaDataDB(self.package, self.publisher)
            metadata.descriptor = json.dumps(descriptor)
            db.session.add(metadata)
            db.session.commit()
        rv = self.client.get('/{publisher}/{package}'.format(publisher=self.publisher, package=self.package))
        self.assertNotIn('404', rv.data)
        self.assertIn('Data Files', rv.data)
        self.assertIn('handsontable', rv.data) # cheks handsontable load
        self.assertIn('vega', rv.data) # cheks Vega graph load


        rv = self.client.get('/non-existing/demo-package')
        self.assertIn('404', rv.data)
        self.assertNotIn('handsontable', rv.data) # cheks handsontable not loaded
        self.assertNotIn('vega', rv.data) # cheks graph not loaded


    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()