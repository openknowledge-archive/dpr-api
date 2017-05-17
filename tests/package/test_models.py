# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import boto3
from urlparse import urlparse
from moto import mock_s3
import unittest
import json
from app import create_app
from app.database import db
from app.package.models import Package, PackageStateEnum, PackageTag
from app.profile.models import User, Publisher, UserRoleEnum, PublisherUser


class PackageTestCase(unittest.TestCase):
    def setUp(self):
        self.publisher_one = 'test_publisher1'
        self.publisher_two = 'test_publisher2'
        self.package_one = 'test_package1'
        self.package_two = 'test_package2'
        self.package_three = 'test_package3'
        self.app = create_app()
        self.app.app_context().push()

        with self.app.test_request_context():
            db.drop_all()
            db.create_all()

            user1 = User(name=self.publisher_one)
            publisher1 = Publisher(name=self.publisher_one)
            association1 = PublisherUser(role=UserRoleEnum.owner)
            association1.publisher = publisher1
            user1.publishers.append(association1)

            user2 = User(name=self.publisher_two)
            publisher2 = Publisher(name=self.publisher_two)
            association2 = PublisherUser(role=UserRoleEnum.owner)
            association2.publisher = publisher2
            user2.publishers.append(association2)

            metadata1 = Package(name=self.package_one)
            tag1 = PackageTag(descriptor=dict(name='test_one'))
            metadata1.tags.append(tag1)
            publisher1.packages.append(metadata1)

            metadata2 = Package(name=self.package_two)
            tag2 = PackageTag(descriptor=dict(name='test_two'))
            metadata2.tags.append(tag2)
            publisher1.packages.append(metadata2)

            metadata3 = Package(name=self.package_one)
            tag3 = PackageTag(descriptor=dict(name='test_three'))
            metadata3.tags.append(tag3)
            publisher2.packages.append(metadata3)

            metadata4 = Package(name=self.package_two)
            tag4 = PackageTag(descriptor=dict(name='test_four'))
            metadata4.tags.append(tag4)
            publisher2.packages.append(metadata4)

            metadata5 = Package(name=self.package_three)
            tag5 = PackageTag(descriptor=dict(name='test_four'))
            metadata5.tags.append(tag5)
            publisher2.packages.append(metadata5)

            db.session.add(user1)
            db.session.add(user2)

            db.session.commit()

    def test_composite_key(self):
        res = Package.query.join(Publisher).filter(Publisher.name ==
                                                   self.publisher_one).all()
        self.assertEqual(2, len(res))

    def test_get_by_publisher(self):
        pkg = Package.get_by_publisher(self.publisher_one, self.package_one)
        self.assertEqual(pkg.name, self.package_one)

    def test_get_by_publisher_returns_none_if_no_publisher(self):
        pkg = Package.get_by_publisher('not_a_publisher', self.package_one)
        self.assertIsNone(pkg)

    def test_get_by_publisher_returns_none_if_no_package(self):
        pkg = Package.get_by_publisher(self.publisher_one, 'not_a_package')
        self.assertIsNone(pkg)
        

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
