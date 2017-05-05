import unittest
import json

from app import create_app
from app.database import db
from app.package.schemas import *
from app.package.models import *
from app.profile.schemas import *
from app.profile.models import *
from app.logic import *

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


class DataPackageShowTest(unittest.TestCase):

    def setUp(self):
        self.publisher = 'demo'
        self.package = 'demo-package'
        self.app = create_app()
        self.app.app_context().push()
        self.descriptor = json.loads(open('fixtures/datapackage.json').read())

        with self.app.test_request_context():
            db.drop_all()
            db.create_all()
            create_test_package(self.publisher, self.package, self.descriptor)

    def test_get_package(self):
        # result is a dict ready for passing to templates or API
        package = get_package(self.publisher, self.package)
        self.assertEqual(package['descriptor']['name'], self.package)
        self.assertEqual(package['descriptor']['owner'], self.publisher)
        self.assertTrue(package.get('datapackag_url'))
        self.assertEqual(package['views'], self.descriptor['views'])
        self.assertEqual(package['short_readme'], '')

    def test_returns_none_if_package_not_found(self):
        package = get_package(self.publisher, 'unknown')
        self.assertIsNone(package)
        package = get_package('unknown', self.package)
        self.assertIsNone(package)
        package = get_package('unknown', 'unknown')
        self.assertIsNone(package)

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()


class PackageTest(unittest.TestCase):

    def setUp(self):
        self.publisher = 'demo'
        self.package = 'demo-package'
        self.app = create_app()
        self.app.app_context().push()
        self.descriptor = json.loads(open('fixtures/datapackage.json').read())

        with self.app.test_request_context():
            db.drop_all()
            db.create_all()
            create_test_package(self.publisher, self.package, self.descriptor)


    def test_get_metadata(self):
        metadata = get_metadata_for_package(self.publisher, self.package)
        self.assertEqual(metadata['descriptor'], self.descriptor)
        self.assertEqual(metadata['publisher'], self.publisher)
        self.assertEqual(metadata['name'], self.package)
        self.assertEqual(metadata['readme'], '')
        self.assertEqual(metadata['id'], 1)

    def test_returns_none_if_package_not_found(self):
        package = get_metadata_for_package(self.publisher, 'unknown')
        self.assertIsNone(package)
        package = get_metadata_for_package('unknown', self.package)
        self.assertIsNone(package)
        package = get_metadata_for_package('unknown', 'unknown')
        self.assertIsNone(package)

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()


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


    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()
