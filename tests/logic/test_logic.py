import unittest
import json

from mock import patch
from app import create_app
from app.database import db
from app.package.models import *
from app.profile.models import *
from app.logic import *
from app.utils import InvalidUsage

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
        self.datapackage_url = 'https://bits.datapackaged.com/metadata/' \
                          '{pub}/{pack}/_v/latest/datapackage.com'.\
            format(pub=self.publisher, pack=self.package)

        with self.app.test_request_context():
            db.drop_all()
            db.create_all()
            create_test_package(self.publisher, self.package, self.descriptor)


    @patch('app.logic.db_logic.create_or_update_package')
    @patch('app.package.models.BitStore.get_metadata_body')
    @patch('app.package.models.BitStore.get_readme_object_key')
    @patch('app.package.models.BitStore.get_s3_object')
    @patch('app.package.models.BitStore.change_acl')
    def test_finalize_package_publish_returns_queued_if_fine(
                                    self, change_acl, get_s3_object,
                                    get_readme_object_key,
                                    get_metadata_body, create_or_update):
        get_metadata_body.return_value = json.dumps(dict(name='package'))
        create_or_update.return_value = None
        get_readme_object_key.return_value = ''
        get_s3_object.return_value = ''
        change_acl.return_value = None
        status = finalize_package_publish(1, self.datapackage_url)
        self.assertEqual(status, 'queued')


    @patch('app.logic.db_logic.create_or_update_package')
    @patch('app.package.models.BitStore.get_metadata_body')
    @patch('app.package.models.BitStore.get_readme_object_key')
    @patch('app.package.models.BitStore.get_s3_object')
    @patch('app.package.models.BitStore.change_acl')
    def test_finalize_package_publish_throws_400_if_publisher_does_not_exist(
                                    self, change_acl, get_s3_object,
                                    get_readme_object_key,
                                    get_metadata_body, create_or_update):
        get_metadata_body.return_value = json.dumps(dict(name='package'))
        create_or_update.return_value = None
        get_readme_object_key.return_value = ''
        get_s3_object.return_value = ''
        change_acl.return_value = None
        with self.assertRaises(InvalidUsage) as context:
            finalize_package_publish(2, self.datapackage_url)
        self.assertEqual(context.exception.status_code, 400)


    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()

class HelpersTest(unittest.TestCase):


    def setUp(self):
        self.descriptor = json.loads(open('fixtures/datapackage.json').read())


    def test_validate_for_jinja_returns_descriptor_if_no_licenses(self):
        descriptor = validate_for_template(self.descriptor)
        self.assertEqual(self.descriptor, descriptor)

    def test_validate_for_jinja_returns_descriptor_if_licenses_is_list(self):
        self.descriptor['licenses'] = []
        descriptor = validate_for_template(self.descriptor)
        self.assertEqual(self.descriptor, descriptor)

    def test_validate_for_jinja_modifies_descriptor_if_licenses_is_dict(self):
        self.descriptor['licenses'] = {'url': 'test/url', 'type': 'Test'}
        descriptor = validate_for_template(self.descriptor)
        self.assertEqual(descriptor['license'], 'Test')

    def test_validate_for_not_errors_if_licenses_is_dict_and_has_no_type_key(self):
        self.descriptor['licenses'] = {'url': 'test/url'}
        descriptor = validate_for_template(self.descriptor)
        self.assertEqual(descriptor['license'], None)

    def test_validate_for_jinja_removes_licenses_if_invalid_type(self):
        self.descriptor['licenses'] = 1
        descriptor = validate_for_template(self.descriptor)
        self.assertEqual(descriptor.get('licenses'), None)
