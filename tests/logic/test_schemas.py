# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import unittest
import datetime

from app import create_app
from app.database import db
import app.models as models
from app.logic.db_logic import *


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


    def test_schema_for_publisher_user(self):
        user = models.User(name=self.publisher, id=2)
        publisher = models.Publisher(name=self.publisher, id=3)
        association = models.PublisherUser(role=models.UserRoleEnum.owner, user=user, publisher=publisher)
        user.publishers.append(association)

        db.session.add(user)
        db.session.add(publisher)
        db.session.add(association)
        db.session.commit()

        association_schema = PublisherUserSchema()

        self.assertEqual(association_schema.dump(association).data['publisher'], 3)
        self.assertEqual(association_schema.dump(association).data['user'], 2)


    def test_schema_for_publisher(self):
        publisher = models.Publisher(name=self.publisher)
        publisher_schema = PublisherSchema()
        self.assertEqual(publisher_schema.dump(publisher).data['name'], self.publisher)


    def test_nested_relationships(self):

        publisher = models.Publisher(name=self.publisher, id=3)
        user = models.User(name='user', id=2)
        association = models.PublisherUser(role=UserRoleEnum.owner, user=user, publisher=publisher)
        user.publishers.append(association)

        metadata = models.Package(name=self.package)
        tag = models.PackageTag(descriptor={})
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
        publisher = models.Publisher(name=self.publisher, id=3)
        user = models.User(name='user', id=2)
        association = models.PublisherUser(role=models.UserRoleEnum.owner, user=user, publisher=publisher)
        user.publishers.append(association)

        metadata = models.Package(name=self.package, status=models.PackageStateEnum.active)
        tag = models.PackageTag(descriptor={})
        metadata.tags.append(tag)
        publisher.packages.append(metadata)

        db.session.add(user)
        db.session.add(publisher)
        db.session.add(association)
        db.session.commit()

        data = models.Package.query.join(models.Publisher).\
            filter(models.Publisher.name == self.publisher,
                   models.Package.name == self.package,
                   models.Package.status == models.PackageStateEnum.active).\
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


class PublisherSchemaTest(unittest.TestCase):
    def setUp(self):
        self.publisher_name = 'demo'
        self.package_name = 'demo-package'
        self.app = create_app()
        self.app.app_context().push()
        with self.app.app_context():
            db.drop_all()
            db.create_all()
            self.user = models.User()
            self.user.id = 1
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


    def tests_publisher_schema_on_dump(self):
        publisher = models.Publisher.query.filter(models.Publisher.name == self.publisher_name).first()
        publisher_schema = PublisherSchema(
                only=('joined', 'title', 'contact', 'name', 'description')
            )
        publisher = publisher_schema.dump(publisher).data

        self.assertEqual(publisher['name'], 'demo')
        self.assertIsNone(publisher['title'])
        self.assertIsNone(publisher['contact'])
        self.assertIsNone(publisher['description'])


    def tests_publisher_schema_on_dump(self):
        publisher = models.Publisher.query.filter(models.Publisher.name == self.publisher_name).first()
        publisher_schema = PublisherSchema(
                only=('joined', 'title', 'contact', 'name', 'description')
            )
        publisher = publisher_schema.dump(publisher).data

        self.assertEqual(publisher['name'], 'demo')
        self.assertIsNone(publisher['title'])
        self.assertIsNone(publisher['contact'])
        self.assertIsNone(publisher['description'])


    def test_schema_for_publisher_with_pubic_contact(self):
        publisher = models.Publisher(name=self.publisher, contact_public=True)
        publisher_schema = PublisherSchema()
        expected = {'country': None, 'email': None, 'phone': None}
        self.assertEqual(publisher_schema.dump(publisher).data['contact'], expected)


    def test_publisher_schema_on_load(self):
        publisher = models.Publisher.query.filter(models.Publisher.name == self.publisher_name).first()
        publisher_schema = PublisherSchema()
        dump = publisher_schema.dump(publisher).data
        load = publisher_schema.load(dump, session = db.session).data

        self.assertEqual(publisher.name, 'demo')
        self.assertIsNone(publisher.title)
        self.assertIsNone(publisher.contact_public)
        self.assertIsNone(publisher.description)


    def test_publisher_schema_on_load_creates_publisher_if_user_exists(self):
        dump = {
            'name': 'test_publisher',
            'users': [{'user_id': 1, 'role': 'owner'}],
            }
        publisher_schema = PublisherSchema()
        load = publisher_schema.load(dump, session = db.session).data
        db.session.add(load)

        publisher = models.Publisher.query.filter(models.Publisher.name == 'test_publisher').first()
        dump = publisher_schema.dump(publisher).data

        self.assertEqual(dump['name'], 'test_publisher')
        self.assertEqual(dump['users'], [{'publisher_id': 2, 'user_id': 1, 'id': 2}])


    def test_publisher_schema_on_load_creates_publisher_and_packages_from_response(self):
        dump = {
            'name': 'test_publisher',
            'users': [{'user_id': 1, 'role': 'owner'}],
            'packages': [{'name': self.package_name}, {'name': 'new-package'}],
            }
        publisher_schema = PublisherSchema()
        load = publisher_schema.load(dump, session = db.session).data
        db.session.add(load)

        publisher = models.Publisher.query.filter(models.Publisher.name == 'test_publisher').first()
        dump = publisher_schema.dump(publisher).data

        self.assertEqual(dump['name'], 'test_publisher')
        self.assertEqual(dump['users'], [{'publisher_id': 2, 'user_id': 1, 'id': 2}])
        self.assertEqual(dump['packages'], [2,3])


    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()


class UserSchemaTest(unittest.TestCase):
    def setUp(self):
        self.user = 'demo'
        self.email = 'email'
        self.full_name = 'Demo'
        self.app = create_app()
        self.app.app_context().push()
        with self.app.test_request_context():
            db.drop_all()
            db.create_all()
            db.session.commit()


    def test_user_schema_dump(self):
        user = models.User(name=self.user, email=self.email, full_name=self.full_name)
        user_schema = UserSchema()
        serialized_data = user_schema.dump(user).data
        self.assertEqual(serialized_data['name'], self.user)
        self.assertEqual(serialized_data['full_name'], self.full_name)
        self.assertEqual(serialized_data['email'], self.email)


    def test_user_schema_load(self):
        response = dict(
            email = self.email,
            login = self.user,
            name = self.full_name
        )
        user_schema = UserSchema()
        deserialized = user_schema.load(response).data

        self.assertEqual(deserialized.name, self.user)
        self.assertEqual(deserialized.email, self.email)
        self.assertEqual(deserialized.full_name, self.full_name)


    def test_user_schema_creates_secret_on_load(self):
        response = dict(
            email = self.email,
            login = self.user,
            name = self.full_name
        )
        user_schema = UserSchema()
        deserialized = user_schema.load(response).data

        self.assertIsNotNone(deserialized.secret, self.user)


    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()


class PackageSchemaTest(unittest.TestCase):
    def setUp(self):
        self.publisher_name = 'demo'
        self.package_name = 'demo-package'
        self.app = create_app()
        self.app.app_context().push()
        with self.app.app_context():
            db.drop_all()
            db.create_all()
            self.user = models.User()
            self.user.id = 1
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


    def tests_package_schema_on_dump(self):
        package = models.Package.query.join(models.Publisher)\
            .filter(models.Package.name == self.package_name,
                    models.Publisher.name == self.publisher_name).first()
        package_schema = PackageSchema()
        package = package_schema.dump(package).data
        self.assertEqual(package['status'], 'active')
        self.assertEqual(package['publisher'], 1)
        self.assertEqual(package['name'], self.package_name)
        self.assertEqual(package['tags'], [1])
        self.assertFalse(package['private'])
        self.assertEqual(package['id'], 1)


    def tests_package_schema_on_load(self):
        package = models.Package.query.join(models.Publisher)\
            .filter(models.Package.name == self.package_name,
                    models.Publisher.name == self.publisher_name).first()
        package_schema = PackageSchema()
        dump = package_schema.dump(package).data
        load = package_schema.load(dump, session = db.session).data
        self.assertEqual(load.status, models.PackageStateEnum.active)
        self.assertEqual(type(load.publisher), type(self.publisher))
        self.assertEqual(load.name, self.package_name)
        self.assertFalse(load.private)


    def tests_package_schema_on_load_creates_package_in_db(self):
        dump = {
            'status': 'active',
            'publisher': 1,
            'name': 'new-package',
            'tags': [2],
        }
        package_schema = PackageSchema()
        package = package_schema.load(dump, session = db.session).data
        db.session.add(package)

        package = models.Package.query.join(models.Publisher)\
            .filter(models.Package.name == 'new-package',
                    models.Publisher.id == 1).first()
        package = package_schema.dump(package).data
        self.assertEqual(package['status'], 'active')
        self.assertEqual(package['publisher'], 1)
        self.assertEqual(package['name'], 'new-package')
        self.assertEqual(package['tags'], [2])
        self.assertFalse(package['private'])
        self.assertEqual(package['id'], 2)


    def test_package_tag_schema_on_dump(self):
        tag = models.PackageTag.query.join(models.Package)\
            .filter(models.Package.name == self.package_name,
                    models.PackageTag.tag == 'latest').first()
        package_tag_schema = PackageTagSchema()
        tag = package_tag_schema.dump(tag).data
        self.assertEqual(tag['package'], 1)
        self.assertEqual(tag['tag'], 'latest')
        self.assertEqual(tag['id'], 1)
        self.assertEqual(tag['descriptor'], {})


    def tests_package_tag_schema_on_load(self):
        tag = models.PackageTag.query.join(models.Package)\
            .filter(models.Package.name == self.package_name).first()
        package_tag_schema = PackageTagSchema()
        dump = package_tag_schema.dump(tag).data
        load = package_tag_schema.load(dump, session = db.session).data
        self.assertEqual(load.package.id, 1)
        self.assertEqual(load.tag, 'latest')
        self.assertEqual(load.descriptor, {})


    def test_package_tag_schema_on_creates_new_tag(self):
        dump = {
            'package': 1,
            'descriptor': {'new': 'descriptor'},
            'tag': 'new'
        }

        package_tag_schema = PackageTagSchema()
        load = package_tag_schema.load(dump, session = db.session).data

        tag = models.PackageTag.query.join(models.Package)\
            .filter(models.Package.name == self.package_name,
                    models.PackageTag.tag == 'new').first()
        tag = package_tag_schema.dump(tag).data

        self.assertEqual(tag['package'], 1)
        self.assertEqual(tag['tag'], 'new')
        self.assertEqual(tag['id'], 2)
        self.assertEqual(tag['descriptor'], {u'new': u'descriptor'})


    def test_package_tag_schema_on_creates_package_and_new_tag(self):
        dump = {
            'package': 10,
            'descriptor': {'test': 'descriptor'}
        }

        package_tag_schema = PackageTagSchema()
        tag = package_tag_schema.load(dump, session = db.session).data
        db.session.add(tag)

        tag = models.PackageTag.query.join(models.Package).filter(models.Package.id == 10).first()
        tag = package_tag_schema.dump(tag).data

        self.assertEqual(tag['package'], 10)
        self.assertEqual(tag['tag'], 'latest')
        self.assertEqual(tag['id'], 2)
        self.assertEqual(tag['descriptor'], {u'test': u'descriptor'})


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
