# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import unittest
import json

from app import create_app
from app.bitstore import BitStore
from app.database import db
from app.logic import db_logic
from app.profile.models import User, Publisher, PublisherUser, UserRoleEnum
from app.package.models import Package, PackageStateEnum, PackageTag
from app.utils import InvalidUsage

class UserTestCase(unittest.TestCase):
    def setUp(self):
        self.publisher = 'demo'
        self.package = 'demo-package'
        self.app = create_app()
        self.app.app_context().push()
        with self.app.test_request_context():
            db.drop_all()
            db.create_all()
            user = User(id=11,
                        name=self.publisher,
                        secret='supersecret')
            publisher = Publisher(name=self.publisher)
            association = PublisherUser(role=UserRoleEnum.owner)
            association.publisher = publisher
            user.publishers.append(association)

            db.session.add(user)
            db.session.commit()


    def test_find_or_create_creates_user_from_0auth_response_if_not_found(self):
        user_info = dict(email="test@test.com",
                         login="test",
                         name="The Test")
        user = db_logic.find_or_create_user(user_info)
        self.assertEqual(user.name, 'test')


    def test_find_or_create_creates_publisher_as_well(self):
        user_info = dict(email="test@test.com",
                         login="test",
                         name="The Test")
        user = db_logic.find_or_create_user(user_info)
        publisher = Publisher.query.filter_by(name='test').one()
        self.assertEqual(publisher.name, 'test')


    def test_find_or_create_findes_user_from_0auth_response_if_found(self):
        user_info = dict(email="test@test.com",
                         login="demo",
                         name="The Test")
        user = db_logic.find_or_create_user(user_info)
        self.assertEqual(user.name, self.publisher)


    def test_create_user_should_handle_null_email(self):
        user_info = dict(login="test_null_email")
        db_logic.find_or_create_user(user_info)
        user = User.query.filter_by(name='test_null_email').first()
        self.assertIsNotNone(user)
        self.assertIsNone(user.email)
        self.assertIsNone(user.full_name)


    def test_get_user_info(self):
        publisher = db_logic.get_user_by_id(11)
        self.assertEqual(publisher['name'], self.publisher)


    def test_get_user_info_returns_none_if_no_publisher_found(self):
            user_info = db_logic.get_user_by_id(2)
            self.assertIsNone(user_info)


    def test_get_publisher_info(self):
        publisher = db_logic.get_publisher(self.publisher)
        self.assertEqual(publisher['name'], self.publisher)


    def test_get_publisher_info_returns_none_if_no_publisher_found(self):

        publisher = db_logic.get_publisher('not_a_publisher')
        self.assertIsNone(publisher)


    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()


class PackageTestCase(unittest.TestCase):
    def setUp(self):
        self.publisher = 'demo'
        self.package = 'demo-package'
        self.publisher_one = 'test_publisher1'
        self.publisher_two = 'test_publisher2'
        self.package_one = 'test_package1'
        self.package_two = 'test_package2'
        self.package_three = 'test_package3'
        self.descriptor = json.loads(open('fixtures/datapackage.json').read())
        self.app = create_app()
        self.app.app_context().push()

        with self.app.test_request_context():
            db.drop_all()
            db.create_all()

            create_test_package(self.publisher, self.package, self.descriptor)

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

    def test_update_fields_if_instance_present(self):
        metadata = Package.query.join(Publisher) \
            .filter(Publisher.name == self.publisher_one,
                    Package.name == self.package_one).one()

        descriptor = metadata.tags[0].descriptor

        self.assertEqual(descriptor['name'], "test_one")
        db_logic.create_or_update_package(self.package_one, self.publisher_one,
                                 descriptor=json.dumps(dict(name='sub')),
                                 private=True)
        metadata = Package.query.join(Publisher) \
            .filter(Publisher.name == self.publisher_one,
                    Package.name == self.package_one).one()
        descriptor = metadata.tags[0].descriptor
        self.assertEqual(json.loads(descriptor)['name'], "sub")
        self.assertEqual(metadata.private, True)

    def test_insert_if_not_present(self):
        pub = self.publisher_two
        name = "custom_name"

        metadata = Package.query.join(Publisher) \
            .filter(Publisher.name == pub,
                    Package.name == name).all()
        self.assertEqual(len(metadata), 0)
        db_logic.create_or_update_package(name, pub,
                                 descriptor=json.dumps(dict(name='sub')),
                                 private=True)
        metadata = Package.query.join(Publisher) \
            .filter(Publisher.name == pub,
                    Package.name == name).all()
        self.assertEqual(len(metadata), 1)

    def test_should_populate_new_versioned_data_package(self):
        db_logic.create_or_update_package_tag(self.publisher_one,
                                     self.package_two, 'tag_one')
        package = Package.query.join(Publisher) \
            .filter(Publisher.name == self.publisher_one,
                    Package.name == self.package_two).one()

        latest_data = PackageTag.query.join(Package) \
            .filter(Package.id == package.id,
                    PackageTag.tag == 'latest').one()

        tagged_data = PackageTag.query.join(Package) \
            .filter(Package.id == package.id,
                    PackageTag.tag == 'tag_one').one()

        self.assertEqual(latest_data.package_id, tagged_data.package_id)
        self.assertEqual('tag_one', tagged_data.tag)

    def test_should_update_data_package_if_preexists(self):
        with self.app.test_request_context():
            pub = Publisher.query.filter_by(name=self.publisher_one).one()
            package = Package.query.join(Publisher)\
                .filter(Publisher.name == self.publisher_one,
                        Package.name == self.package_two)\
                .one()
            package.tags.append(PackageTag(tag='tag_one', readme='old_readme'))
            pub.packages.append(package)
            db.session.add(pub)
            db.session.commit()

        package = Package.query.join(Publisher) \
            .filter(Publisher.name == self.publisher_one,
                    Package.name == self.package_two).one()

        latest_data = PackageTag.query.join(Package) \
            .filter(Package.id == package.id,
                    PackageTag.tag == 'latest').one()

        tagged_data = PackageTag.query.join(Package) \
            .filter(Package.id == package.id,
                    PackageTag.tag == 'tag_one').one()

        self.assertNotEqual(latest_data.readme, tagged_data.readme)

        db_logic.create_or_update_package_tag(self.publisher_one,
                                     self.package_two,
                                     'tag_one')
        tagged_data = PackageTag.query.join(Package) \
            .filter(Package.id == package.id,
                    PackageTag.tag == 'tag_one').one()

        self.assertEqual(latest_data.readme, tagged_data.readme)

    def test_change_status(self):
        data = Package.query.join(Publisher). \
            filter(Publisher.name == self.publisher_one,
                   Package.name == self.package_one).one()
        self.assertEqual(PackageStateEnum.active, data.status)

        db_logic.change_package_status(self.publisher_one, self.package_one,
                                                        PackageStateEnum.deleted)

        data = Package.query.join(Publisher). \
            filter(Publisher.name == self.publisher_one,
                   Package.name == self.package_one).one()
        self.assertEqual(PackageStateEnum.deleted, data.status)

        db_logic.change_package_status(self.publisher_one, self.package_one,
                              status=PackageStateEnum.active)

        data = Package.query.join(Publisher). \
            filter(Publisher.name == self.publisher_one,
                   Package.name == self.package_one).one()
        self.assertEqual(PackageStateEnum.active, data.status)

    def test_update_status_with_tag(self):
        db_logic.create_or_update_package_tag(self.publisher_two,
                                     self.package_three,
                                     '1.0')
        db_logic.create_or_update_package_tag(self.publisher_two,
                                     self.package_three,
                                     '1.1')
        status = db_logic.change_package_status(self.publisher_two,
                                       self.package_three,
                                       PackageStateEnum.deleted)
        self.assertTrue(status)

    def test_delete_with_tag(self):
        db_logic.create_or_update_package_tag(self.publisher_two,
                                     self.package_three,
                                     '1.0')
        db_logic.create_or_update_package_tag(self.publisher_two,
                                     self.package_three,
                                     '1.1')
        status = db_logic.delete_data_package(self.publisher_two, self.package_three)
        self.assertTrue(status)

    def test_return_true_if_delete_data_package_success(self):
        status = db_logic.delete_data_package(self.publisher_one,
                                             self.package_one)
        self.assertTrue(status)
        data = Package.query.join(Publisher). \
            filter(Publisher.name == self.publisher_one,
                   Package.name == self.package_one).all()
        self.assertEqual(0, len(data))
        data = Publisher.query.all()
        self.assertEqual(3, len(data))

    def test_is_package_exists(self):
        status = db_logic.package_exists(self.publisher_one, self.package_one)
        self.assertTrue(status)
        status = db_logic.package_exists(self.publisher_one, 'non-exists-package')
        self.assertFalse(status)


    def test_get_metadata(self):
        metadata = db_logic.get_metadata_for_package(self.publisher, self.package)
        self.assertEqual(metadata['descriptor'], self.descriptor)
        self.assertEqual(metadata['publisher'], self.publisher)
        self.assertEqual(metadata['name'], self.package)
        self.assertEqual(metadata['readme'], '')
        self.assertEqual(metadata['id'], 1)


    def test_returns_none_if_package_not_found(self):
        package = db_logic.get_metadata_for_package(self.publisher, 'unknown')
        self.assertIsNone(package)
        package = db_logic.get_metadata_for_package('unknown', self.package)
        self.assertIsNone(package)
        package = db_logic.get_metadata_for_package('unknown', 'unknown')
        self.assertIsNone(package)


    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()


def create_test_package(publisher='demo', package='demo-package', descriptor={}):

    user = User(name=publisher)
    publisher = Publisher(name=publisher)
    association = PublisherUser(role=UserRoleEnum.owner)
    association.publisher = publisher
    user.publishers.append(association)

    metadata = Package(name=package)
    tag = PackageTag(descriptor=descriptor)
    metadata.tags.append(tag)
    publisher.packages.append(metadata)

    db.session.add(user)
    db.session.commit()
