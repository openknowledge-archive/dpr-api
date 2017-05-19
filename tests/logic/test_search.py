# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import unittest
from app import create_app
from app.database import db
import app.logic as logic
from app.logic.search import DataPackageQuery
from app.profile.models import Publisher
from app.package.models import Package, PackageTag


class DataPackageQueryTestCase(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.app.app_context().push()
        self.pub1_name = 'pub1'
        self.pub2_name = 'pub2'
        with self.app.test_request_context():
            db.drop_all()
            db.create_all()

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

    def test_should_return_query_and_filter(self):
        query_string = "abc publisher:core"
        dpq = DataPackageQuery(query_string)
        query, filters = dpq._parse_query_string()
        self.assertEqual('abc', query)
        self.assertEqual('publisher:core', filters[0])

    def test_should_return_query(self):
        query_string = "abc"
        dpq = DataPackageQuery(query_string)
        query, filters = dpq._parse_query_string()
        self.assertEqual('abc', query)
        self.assertEqual(0, len(filters))

    def test_should_contain_multiple_filters(self):
        query_string = "publisher:pub1 publisher:pub2 abc "
        dpq = DataPackageQuery(query_string)
        query, filters = dpq._parse_query_string()
        self.assertEqual('abc', query)
        self.assertEqual(2, len(filters))

    def test_should_take_first_query_occurrence(self):
        query_string = "bca publisher:pub1 publisher:pub2 abc "
        dpq = DataPackageQuery(query_string)
        query, filters = dpq._parse_query_string()
        self.assertEqual('bca', query)
        self.assertEqual(2, len(filters))

        query_string = "publisher:pub1 publisher:pub2 abc "
        dpq = DataPackageQuery(query_string)
        query, filters = dpq._parse_query_string()
        self.assertEqual('abc', query)
        self.assertEqual(2, len(filters))

    def test_sql_query_should_contain_join_stmt(self):
        query_string = "abc publisher:core"
        dpq = DataPackageQuery(query_string)
        query, filters = dpq._parse_query_string()
        self.assertEqual(2, len(dpq._build_sql_query(query, filters)
                                ._join_entities))

    def test_sql_query_should_contain_one_like_stmt(self):
        query_string = "abc"
        dpq = DataPackageQuery(query_string)
        query, filters = dpq._parse_query_string()
        self.assertEqual(3, len(dpq._build_sql_query(query, filters)
                                .whereclause._from_objects))

    def test_sql_query_should_not_contain_like_stmt(self):
        query_string = "*"
        dpq = DataPackageQuery(query_string)
        query, filters = dpq._parse_query_string()
        self.assertIsNone(dpq._build_sql_query(query, filters)
                          .whereclause)

    def test_get_data_should_return_all_data_contains_query_string(self):
        query_string = "*"
        dpq = DataPackageQuery(query_string)
        self.assertEqual(6, len(dpq.get_data()))

    def test_get_data_should_return_all_data_by_publisher(self):
        query_string = "* publisher:pub1"
        dpq = DataPackageQuery(query_string)
        self.assertEqual(3, len(dpq.get_data()))

        query_string = "* publisher:pub3"
        dpq = DataPackageQuery(query_string)
        self.assertEqual(0, len(dpq.get_data()))

    def test_should_return_data_package_containing_query(self):
        query_string = "none-query publisher:pub1"
        dpq = DataPackageQuery(query_string)
        self.assertEqual(0, len(dpq.get_data()))

        query_string = "one publisher:pub1"
        dpq = DataPackageQuery(query_string)
        self.assertEqual(1, len(dpq.get_data()))
        self.assertEqual('pub1', dpq.get_data()[0]['publisher_name'])

        query_string = "details publisher:pub1"
        dpq = DataPackageQuery(query_string)
        self.assertEqual(3, len(dpq.get_data()))

        query_string = "details publisher:pub1 publisher:pub2"
        dpq = DataPackageQuery(query_string)
        self.assertEqual(6, len(dpq.get_data()))

    def test_should_return_data_package_with_limit(self):

        query_string = "details publisher:pub1"
        dpq = DataPackageQuery(query_string, limit=5)
        self.assertEqual(3, len(dpq.get_data()))

        query_string = "details publisher:pub1 publisher:pub2"
        dpq = DataPackageQuery(query_string, limit=3)
        self.assertEqual(3, len(dpq.get_data()))

    def test_limit_should_be_maximum_1000(self):
        dpq = DataPackageQuery('details publisher:pub1', limit=1005)
        self.assertEqual(1000, dpq.limit)

    def test_should_not_visible_after_soft_delete(self):
        logic.Package.delete(self.pub1_name, 'pack1')
        query_string = "details publisher:pub1"
        dpq = DataPackageQuery(query_string, limit=3)
        self.assertEqual(2, len(dpq.get_data()))

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
