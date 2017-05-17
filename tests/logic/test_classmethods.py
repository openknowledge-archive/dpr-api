# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import unittest

from app import create_app
from app.database import db
import app.logic.db_logic as logic
import app.models as models


class LogicBaseTest(unittest.TestCase):
    def setUp(self):
        self.publisher_name = 'demo'
        self.package_name = 'demo-package'
        self.app = create_app()
        self.app.app_context().push()
        with self.app.app_context():
            db.drop_all()
            db.create_all()
            self.user = models.User()
            self.user.email, self.user.name, self.user.secret = \
                'demot@test.com', self.publisher_name, 'super_secret'
            self.publisher = models.Publisher(name=self.publisher_name)
            self.association = models.PublisherUser(role=models.UserRoleEnum.owner)
            self.metadata = models.Package(name=self.package_name)
            self.metadata.tags.append(models.PackageTag(descriptor={}))
            self.publisher.packages.append(self.metadata)
            self.association.publisher = self.publisher
            self.user.publishers.append(self.association)

            db.session.add(self.user)
            db.session.commit()


    def tests_logic_base_serialization(self):
        pkg = models.Package.get_by_publisher(self.publisher_name, self.package_name)
        logic.LogicBase.schema = logic.PackageSchema
        pkg_serialized = logic.LogicBase.serialize(pkg)

        self.assertEqual(pkg_serialized['status'], 'active')
        self.assertEqual(pkg_serialized['publisher'], 1)
        self.assertEqual(pkg_serialized['name'], self.package_name)
        self.assertEqual(pkg_serialized['tags'], [1])
        self.assertFalse(pkg_serialized['private'])
        self.assertEqual(pkg_serialized['id'], 1)

    def tests_logic_base_returns_none_if_instance_is_none(self):
        pkg = None
        logic.LogicBase.schema = logic.PackageSchema
        pkg_serialized = logic.LogicBase.serialize(pkg)

        self.assertIsNone(pkg_serialized)

    def tests_logic_base_deserialization(self):
        pkg = models.Package.get_by_publisher(self.publisher_name, self.package_name)
        logic.LogicBase.schema = logic.PackageSchema
        # get serialized
        pkg_serialized = logic.LogicBase.serialize(pkg)
        pkg_deserialized = logic.LogicBase.deserialize(pkg_serialized)

        self.assertTrue(isinstance(pkg_deserialized, models.Package))
        self.assertEqual(pkg_deserialized.status, models.PackageStateEnum.active)
        self.assertEqual(pkg_deserialized.name, self.package_name)
        self.assertFalse(pkg_deserialized.private)

    def tests_logic_base_deserialization_dees_not_fail_on_empty_obj(self):
        pkg = dict()
        logic.LogicBase.schema = logic.PackageSchema
        pkg_deserialized = logic.LogicBase.deserialize(pkg)

        self.assertTrue(isinstance(pkg_deserialized, models.Package))
        self.assertIsNone(pkg_deserialized.status)
        self.assertIsNone(pkg_deserialized.name)


    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()


class PackageClassMethodsTest(unittest.TestCase):
    def setUp(self):
        self.publisher_name = 'demo'
        self.package_name = 'demo-package'
        self.app = create_app()
        self.app.app_context().push()
        with self.app.app_context():
            db.drop_all()
            db.create_all()
            self.user = models.User()
            self.user.email, self.user.name, self.user.secret = \
                'demot@test.com', self.publisher_name, 'super_secret'
            self.publisher = models.Publisher(name=self.publisher_name)
            self.association = models.PublisherUser(role=models.UserRoleEnum.owner)
            self.metadata = models.Package(name=self.package_name)
            self.metadata.tags.append(models.PackageTag(descriptor={}))
            self.publisher.packages.append(self.metadata)
            self.association.publisher = self.publisher
            self.user.publishers.append(self.association)

            db.session.add(self.user)
            db.session.commit()


    def tests_package_get_method(self):
        pkg = logic.Package.get(self.publisher_name, self.package_name)

        self.assertEqual(pkg['status'], 'active')
        self.assertEqual(pkg['publisher'], 1)
        self.assertEqual(pkg['name'], self.package_name)
        self.assertEqual(pkg['tags'], [1])
        self.assertFalse(pkg['private'])
        self.assertEqual(pkg['id'], 1)

    def tests_package_get_returns_none_if_no_package(self):
        pkg = logic.Package.get(self.publisher_name, 'not-a-package')
        self.assertIsNone(pkg)

    def tests_package_get_returns_none_if_no_publisher(self):
        pkg = logic.Package.get('not-a-publisher', self.publisher_name)
        self.assertIsNone(pkg)


    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()


class PublisherClassMethodsTest(unittest.TestCase):
    def setUp(self):
        self.publisher_name = 'demo'
        self.package_name = 'demo-package'
        self.app = create_app()
        self.app.app_context().push()
        with self.app.app_context():
            db.drop_all()
            db.create_all()
            self.user = models.User()
            self.user.email, self.user.name, self.user.secret = \
                'demot@test.com', self.publisher_name, 'super_secret'
            self.publisher = models.Publisher(name=self.publisher_name)
            self.association = models.PublisherUser(role=models.UserRoleEnum.owner)
            self.metadata = models.Package(name=self.package_name)
            self.metadata.tags.append(models.PackageTag(descriptor={}))
            self.publisher.packages.append(self.metadata)
            self.association.publisher = self.publisher
            self.user.publishers.append(self.association)

            db.session.add(self.user)
            db.session.commit()


    def tests_publisher_get_method(self):
        pub = logic.Publisher.get(self.publisher_name)
        self.assertEqual(pub['name'], self.publisher_name)

    def tests_publisher_get_returns_none_if_no_publisher(self):
        pub = logic.Publisher.get('not-a-publisher')
        self.assertIsNone(pub)

    def test_publisher_create_method_loads_in_db_new_publisher(self):
        metadata = {
            'name': 'new-publisher'
        }
        pub = logic.Publisher.create(metadata)
        created_pub = models.Publisher.query.get(pub.id)
        self.assertEqual(created_pub.name, 'new-publisher')

    def test_publisher_create_method_creates_user_publisher_relaitontion_if_user_exists(self):
        metadata = {
            'name': 'new-publisher',
            'users': [{'role': 'owner', 'user_id': 1}]
        }
        pub = logic.Publisher.create(metadata)
        pub_usr = models.PublisherUser.query.filter_by(publisher_id=pub.id).first()
        self.assertEqual(pub_usr.publisher_id, 2)
        self.assertEqual(pub_usr.publisher_id, pub.id)
        self.assertEqual(pub_usr.role, models.UserRoleEnum.owner)
        self.assertEqual(pub_usr.publisher.name, 'new-publisher')
        self.assertEqual(pub_usr.user.name, self.publisher_name)


    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()


class UserClassMethodsTest(unittest.TestCase):
    def setUp(self):
        self.publisher_name = 'demo'
        self.package_name = 'demo-package'
        self.app = create_app()
        self.app.app_context().push()
        with self.app.app_context():
            db.drop_all()
            db.create_all()
            self.user = models.User()
            self.user.email, self.user.name, self.user.secret = \
                'demot@test.com', self.publisher_name, 'super_secret'
            self.publisher = models.Publisher(name=self.publisher_name)
            self.association = models.PublisherUser(role=models.UserRoleEnum.owner)
            self.metadata = models.Package(name=self.package_name)
            self.metadata.tags.append(models.PackageTag(descriptor={}))
            self.publisher.packages.append(self.metadata)
            self.association.publisher = self.publisher
            self.user.publishers.append(self.association)

            db.session.add(self.user)
            db.session.commit()


    def tests_user_get_method(self):
        usr = logic.User.get(1)
        self.assertEqual(usr['name'], self.publisher_name)

    def tests_user_get_returns_none_if_no_user(self):
        usr = logic.User.get(2)
        self.assertIsNone(usr)

    def test_user_create_method_loads_in_db_new_user(self):
        metadata = {
            'email': 'new@test.com',
            'name': 'new-user',
            'full_name': 'New User',
        }
        usr = logic.User.create(metadata)
        created_usr = models.User.query.get(usr.id)
        self.assertEqual(created_usr.email, 'new@test.com')
        self.assertEqual(created_usr.name, 'new-user')
        self.assertEqual(created_usr.full_name, 'New User')


    def test_user_create_method_creates_user_publisher_relaitontion_if_publisher_exists(self):
        metadata = {
            'email': 'new@test.com',
            'name': 'new-user',
            'full_name': 'New User',
            'publishers': [{'role': 'owner', 'publisher_id': 1}]
        }
        usr = logic.User.create(metadata)
        pub_usr = models.PublisherUser.query.filter_by(user_id=usr.id).first()
        self.assertEqual(pub_usr.publisher_id, 1)
        self.assertEqual(pub_usr.user_id, usr.id)
        self.assertEqual(pub_usr.role, models.UserRoleEnum.owner)
        self.assertEqual(pub_usr.publisher.name, self.publisher_name)
        self.assertEqual(pub_usr.user.name, 'new-user')


    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()
