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

        assert 'demo' in catalog._cache
        assert 'demo-package' in catalog._cache['demo'] 
        assert catalog._cache['demo']['demo-package'] == datapackage
    
    def test_get(self):
        datapackage = json.loads(open('fixtures/datapackage.json').read())
        datapackage['owner'] = 'demo'
        catalog = Catalog()
        catalog.load([datapackage])
        result = catalog.get('demo', 'demo-package')
        assert result == datapackage
        # test unknown owner
        result = catalog.get('anon', 'demo-package')
        assert result is None
        
    def test_query(self):
        datapackage = json.loads(open('fixtures/datapackage.json').read())
        datapackage['owner'] = 'demo'
        catalog = Catalog()
        catalog.load([datapackage])
        
        assert catalog.query() == [datapackage]

    def test_by_owner(self):
        datapackage = json.loads(open('fixtures/datapackage.json').read())
        datapackage['owner'] = 'demo'  
        catalog = Catalog()
        catalog.load([datapackage])
        
        assert catalog.by_owner('demo') == [datapackage]
        assert catalog.by_owner('anon') == []
   