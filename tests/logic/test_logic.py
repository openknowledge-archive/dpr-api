import unittest
import json

from app import create_app
from app.database import db
from app.logic import *
from app.package.models import Package, PackageTag
from app.profile.models import Publisher, User, PublisherUser, UserRoleEnum

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
