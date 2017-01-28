# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import unittest
from app import create_app
from app.database import db
from app.search.models import DataPackageQuery
from app.package.models import Package, Publisher


class DataPackageQueryTestCase(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.app.app_context().push()
        with self.app.test_request_context():
            db.drop_all()
            db.create_all()
            self.pub1_name = 'pub1'
            self.pub2_name = 'pub2'
            self.pub1 = Publisher(name=self.pub1_name)
            self.pub2 = Publisher(name=self.pub2_name)
            self.pub1.packages.append(Package(name='pack1', descriptor='{"title": "pack1 details one"}',
                                              readme="Big readme one"))
            self.pub1.packages.append(Package(name='pack2', descriptor='{"title": "pack2 details two"}',
                                              readme="Big readme two"))
            self.pub1.packages.append(Package(name='pack3', descriptor='{"title": "pack3 details three"}'))

            self.pub2.packages.append(Package(name='pack4', descriptor='{"title": "pack4 details four"}'))
            self.pub2.packages.append(Package(name='pack5', descriptor='{"title": "pack5 details five"}'))
            self.pub2.packages.append(Package(name='pack6', descriptor='{"title": "pack6 details six"}'))
            db.session.add(self.pub1)
            db.session.add(self.pub2)
            db.session.commit()

    def test_should_return_query_and_filter(self):
        query_string = "abc publisher:core"
        dpq = DataPackageQuery(query_string)
        self.assertEqual('abc', dpq.query)
        self.assertEqual('publisher', dpq.filterClass)
        self.assertEqual('core', dpq.filterTerm)

    def test_should_return_query(self):
        query_string = "abc"
        dpq = DataPackageQuery(query_string)
        self.assertEqual('abc', dpq.query)
        self.assertEqual(None, dpq.filterClass)
        self.assertEqual(None, dpq.filterTerm)

    def test_sql_query_should_contain_join_stmt(self):
        query_string = "abc publisher:core"
        dpq = DataPackageQuery(query_string)
        self.assertEqual(1, len(dpq._build_sql_query()._join_entities))

    def test_sql_query_should_not_contain_join_stmt(self):
        query_string = "abc"
        dpq = DataPackageQuery(query_string)
        self.assertEqual(0, len(dpq._build_sql_query()._join_entities))

    def test_sql_query_should_contain_one_like_stmt(self):
        query_string = "abc"
        dpq = DataPackageQuery(query_string)
        self.assertEqual(1, len(dpq._build_sql_query().whereclause._from_objects))

    def test_sql_query_should_not_contain_like_stmt(self):
        query_string = "*"
        dpq = DataPackageQuery(query_string)
        self.assertIsNone(dpq._build_sql_query().whereclause)

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

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
