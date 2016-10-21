from app import create_app
from flask import json
import unittest
from app.mod_site.models import Catalog


class CatalogTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()

    def test_load(self):
        datapackage = json.loads(open('fixtures/datapackage.json').read())
        datapackage['owner'] = 'demo'
        catalog = Catalog()
        catalog.load([datapackage])

        self.assertIn('demo',catalog._cache)
        self.assertIn('demo-package', catalog._cache['demo'] )
        self.assertEqual(catalog._cache['demo']['demo-package'], datapackage)
    
    def test_get(self):
        datapackage = json.loads(open('fixtures/datapackage.json').read())
        datapackage['owner'] = 'demo'
        catalog = Catalog()
        catalog.load([datapackage])
        result = catalog.get('demo', 'demo-package')
        self.assertEqual(result, datapackage)
        # test unknown owner
        result = catalog.get('anon', 'demo-package')
        self.assertIsNone(result)
        
    def test_query(self):
        datapackage = json.loads(open('fixtures/datapackage.json').read())
        datapackage['owner'] = 'demo'
        catalog = Catalog()
        catalog.load([datapackage])
        
        self.assertEqual(catalog.query(), [datapackage])

    def test_by_owner(self):
        datapackage = json.loads(open('fixtures/datapackage.json').read())
        datapackage['owner'] = 'demo'  
        catalog = Catalog()
        catalog.load([datapackage])
        
        self.assertEqual(catalog.by_owner('demo'), [datapackage])
        self.assertEqual(catalog.by_owner('anon'), [])

class WebsiteTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app = self.app.test_client()
    
    def test_home_page(self):
        rv = self.app.get('/')
        self.assertNotIn('404', rv.data)

    def test_data_package_page(self):
        rv = self.app.get('/demo/demo-package')
        self.assertNotIn('404', rv.data)
        self.assertIn('handsontable', rv.data) # cheks handsontable load
        self.assertIn('vega', rv.data) # cheks Vega graph load


        rv = self.app.get('/non-existing/demo-package')
        self.assertIn('404', rv.data)
        self.assertNotIn('handsontable', rv.data) # cheks handsontable not loaded
        self.assertNotIn('vega', rv.data) # cheks graph not loaded

