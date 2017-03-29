# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import unittest
import json
from app import create_app
from app.database import db
from app.profile.models import Publisher
from app.package.models import Package, PackageTag


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
            pack1 = Package(name='pack1')
            pack1.tags.append(PackageTag(descriptor={"title": "pack1 details one"},
                                         readme="Big readme one"))
            self.pub1.packages.append(pack1)

            pack2 = Package(name='pack2')
            pack2.tags.append(PackageTag(descriptor={"title": "pack2 details two"},
                                         readme="Big readme two"))
            self.pub1.packages.append(pack2)

            pack3 = Package(name='pack3')
            pack3.tags.append(PackageTag(descriptor={"title": "pack3 details three"}))
            self.pub1.packages.append(pack3)

            pack4 = Package(name='pack4')
            pack4.tags.append(PackageTag(descriptor={"title": "pack4 details four"}))
            self.pub2.packages.append(pack4)

            pack5 = Package(name='pack5')
            pack5.tags.append(PackageTag(descriptor={"title": "pack5 details five"}))
            self.pub2.packages.append(pack5)

            pack6 = Package(name='pack6')
            pack6.tags.append(PackageTag(descriptor={"title": "pack6 details six"}))
            self.pub2.packages.append(pack6)

            db.session.add(self.pub1)
            db.session.add(self.pub2)
            db.session.commit()

    def test_should_return_data_package_filter_by_publisher(self):
        url = "/api/search/package?q=* publisher:pub1"
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

    def test_should_return_max_result_set_by_limit(self):
        url = "/api/search/package?limit=3"
        response = self.client.get(url)
        result = json.loads(response.data)
        self.assertEqual(200, response.status_code)
        self.assertEqual(3, len(result['items']))

    def test_should_return_20_result_if_limit_invalid(self):
        with self.app.test_request_context():
            pub = Publisher(name='big_publisher')
            for i in range(0, 30):
                pack = Package(name='pack{i}'.format(i=i))
                pack.tags.append(PackageTag(descriptor={"title": "pack1 details one"},
                                            readme="Big readme one"))
                pub.packages\
                    .append(pack)
            db.session.add(pub)
            db.session.commit()

        url = "/api/search/package?limit=lem"
        response = self.client.get(url)
        result = json.loads(response.data)
        self.assertEqual(200, response.status_code)
        self.assertEqual(20, len(result['items']))

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
