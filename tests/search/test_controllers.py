# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import unittest
import json
from app import create_app
from app.database import db
from app.package.models import Package, Publisher


class SearchPackagesTestCase(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.app.app_context().push()
        self.client = self.app.test_client()
        with self.app.test_request_context():
            db.drop_all()
            db.create_all()
            self.pub1_name = 'pub1'
            self.pub2_name = 'pub2'
            self.pub1 = Publisher(name=self.pub1_name)
            self.pub2 = Publisher(name=self.pub2_name)
            self.pub1.packages.append(Package(name='pack1', descriptor={"title": "pack1 details one"},
                                              readme="Big readme one"))
            self.pub1.packages.append(Package(name='pack2', descriptor={"title": "pack2 details two"},
                                              readme="Big readme two"))
            self.pub1.packages.append(Package(name='pack3', descriptor={"title": "pack3 details three"}))

            self.pub2.packages.append(Package(name='pack4', descriptor={"title": "pack4 details four"}))
            self.pub2.packages.append(Package(name='pack5', descriptor={"title": "pack5 details five"}))
            self.pub2.packages.append(Package(name='pack6', descriptor={"title": "pack6 details six"}))
            db.session.add(self.pub1)
            db.session.add(self.pub2)
            db.session.commit()

    def test_should_return_data_package_filter_by_publisher(self):
        url = "/api/search/package?q=* publisher:pub1".format(name=self.pub1_name)
        response = self.client.get(url)
        result = json.loads(response.data)
        self.assertEqual(200, response.status_code)
        self.assertEqual(3, len(result['items']))

    def test_should_return_data_packages_max_to_limit(self):
        url = "/api/search/package?q="
        response = self.client.get(url)
        result = json.loads(response.data)
        self.assertEqual(200, response.status_code)
        self.assertEqual(6, len(result['items']))

    def test_should_return_data_packages_for_blank_query(self):
        url = "/api/search/package"
        response = self.client.get(url)
        result = json.loads(response.data)
        self.assertEqual(200, response.status_code)
        self.assertEqual(6, len(result['items']))

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
