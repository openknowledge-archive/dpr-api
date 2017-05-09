# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import unittest

from app import create_app
from app.database import db
from app.package.models import *
from app.profile.models import *
from app.schemas import *


class SchemaTest(unittest.TestCase):
    def setUp(self):
        self.package = 'demo-package'
        self.publisher = 'demo'
        self.app = create_app()
        self.app.app_context().push()
        with self.app.test_request_context():
            db.drop_all()
            db.create_all()
            db.session.commit()


    def test_schema_for_package(self):
        package = Package(name=self.package)
        package_schema = PackageSchema()
        self.assertEqual(package_schema.dump(package).data['name'], self.package)


    def test_schema_for_tag_package(self):
        tag = PackageTag(tag='first')
        package_tag_schema = PackageTagSchema()
        self.assertEqual(package_tag_schema.dump(tag).data['tag'], 'first')


    def test_schema_for_user(self):
        user = User(name=self.publisher)
        user_schema = UserSchema()
        self.assertEqual(user_schema.dump(user).data['name'], self.publisher)

    def test_schema_for_publisher_user(self):
        user = User(name=self.publisher, id=2)
        publisher = Publisher(name=self.publisher, id=3)
        association = PublisherUser(role=UserRoleEnum.owner, user=user, publisher=publisher)
        user.publishers.append(association)

        db.session.add(user)
        db.session.add(publisher)
        db.session.add(association)
        db.session.commit()

        association_schema = PublisherUserSchema()

        self.assertEqual(association_schema.dump(association).data['publisher'], 3)
        self.assertEqual(association_schema.dump(association).data['user'], 2)


    def test_schema_for_publisher(self):
        publisher = Publisher(name=self.publisher)
        publisher_schema = PublisherSchema()
        self.assertEqual(publisher_schema.dump(publisher).data['name'], self.publisher)


    def test_nested_relationships(self):

        publisher = Publisher(name=self.publisher, id=3)
        user = User(name='user', id=2)
        association = PublisherUser(role=UserRoleEnum.owner, user=user, publisher=publisher)
        user.publishers.append(association)

        metadata = Package(name=self.package)
        tag = PackageTag(descriptor={})
        metadata.tags.append(tag)
        publisher.packages.append(metadata)

        db.session.add(user)
        db.session.add(publisher)
        db.session.add(association)
        db.session.commit()

        publisher_schema = PublisherSchema()
        user_schema = UserSchema()
        association_schema = PublisherUserSchema()
        package_schema = PackageSchema()
        package_tag_schema = PackageTagSchema()

        self.assertEqual(publisher_schema.dump(publisher).data['name'], self.publisher)
        self.assertEqual(publisher_schema.dump(publisher).data['users'],
                                    [{'publisher_id': 3, 'user_id': 2, 'id': 1}])
        self.assertEqual(user_schema.dump(user).data['name'], 'user')
        self.assertEqual(user_schema.dump(user).data['publishers'],
                                    [{'publisher_id': 3, 'user_id': 2, 'id': 1}])
        self.assertEqual(association_schema.dump(association).data['publisher'], 3)
        self.assertEqual(association_schema.dump(association).data['user'], 2)
        self.assertEqual(package_schema.dump(metadata).data['name'], 'demo-package')
        self.assertEqual(package_schema.dump(metadata).data['publisher'], 3)
        self.assertEqual(publisher_schema.dump(publisher).data['name'], self.publisher)

    def test_nested_relationships(self):

        publisher = Publisher(name=self.publisher, id=3)
        user = User(name='user', id=2)
        association = PublisherUser(role=UserRoleEnum.owner, user=user, publisher=publisher)
        user.publishers.append(association)

        metadata = Package(name=self.package, status=PackageStateEnum.active)
        tag = PackageTag(descriptor={})
        metadata.tags.append(tag)
        publisher.packages.append(metadata)

        db.session.add(user)
        db.session.add(publisher)
        db.session.add(association)
        db.session.commit()

        data = Package.query.join(Publisher).\
            filter(Publisher.name == self.publisher,
                   Package.name == self.package,
                   Package.status == PackageStateEnum.active).\
            first()
        metadata_schema = PackageMetadataSchema()
        result = metadata_schema.dump(data)
        expected = {
            'readme': '',
            'publisher': 'demo',
            'id': 1,
            'descriptor': {},
            'name': 'demo-package'
        }
        self.assertEqual(result.data, expected)

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()


class CustomSchemaTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.app_context().push()


    def test_user_info_schema_works_fine_if_response_has_email(self):
        response = {'email': 'test@email.com', 'name': 'test', 'login': 'test'}
        user_info_schema = UserInfoSchema()
        user_info = user_info_schema.load(response).data
        expected = response
        self.assertEqual(expected, user_info)


    def test_user_info_schema_works_fine_if_response_has_no_email(self):
        response = {'name': 'test', 'login': 'test'}
        response['emails'] = [
            {'email': 'test@email.com', 'primary': 'true'},
            {'email': 'other@email.com', 'primary': 'false'}]
        user_info_schema = UserInfoSchema()
        user_info = user_info_schema.load(response).data
        expected = {'name': 'test', 'login': 'test', 'email': 'test@email.com'}
        self.assertEqual(expected, user_info)


    def test_user_info_schema_thrwos_404_if_no_email_provided(self):
        response = {'name': 'test', 'login': 'test'}
        user_info_schema = UserInfoSchema()
        with self.assertRaises(InvalidUsage) as context:
            user_info_schema.load(response).data
        self.assertEqual(context.exception.status_code, 404)
