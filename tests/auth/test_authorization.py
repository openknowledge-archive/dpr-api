# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import unittest

from app import create_app
from app.auth.authorization import is_allowed
from app.database import db
from app.package.models import MetaDataDB, User, Publisher, \
    PublisherUser, UserRoleEnum


class AuthorizationTestCase(unittest.TestCase):
    user_name = "test_user"

    def setUp(self):
        self.app = create_app()
        self.app.app_context().push()
        with self.app.test_request_context():
            db.drop_all()
            db.create_all()

            self.user = User(id=11,
                             name=self.user_name,
                             secret='supersecret',
                             auth0_id="123|auth0")

            self.publisher = Publisher(name=self.user_name)
            self.publisher.packages.append(MetaDataDB(name='test_package'))

            association = PublisherUser(role=UserRoleEnum.owner)
            association.publisher = self.publisher

            self.user.publishers.append(association)

            self.publisher1 = Publisher(name="test_publisher")
            self.publisher1.packages.append(MetaDataDB(name='test_package'))

            association1 = PublisherUser(role=UserRoleEnum.member)
            association1.publisher = self.publisher1

            self.user.publishers.append(association1)

            db.session.add(self.user)

            self.sysadmin = User(id=12,
                                 name='admin',
                                 sysadmin=True)
            db.session.add(self.sysadmin)

            self.random_user = User(id=13,
                                    name='random')
            db.session.add(self.random_user)

            self.publisher2 = Publisher(name="test_publisher1", private=True)
            self.publisher2.packages.append(MetaDataDB(name='test_package',
                                                       private=True))
            db.session.add(self.publisher2)

            self.publisher3 = Publisher(name="test_publisher2", private=False)
            self.publisher3.packages.append(MetaDataDB(name='test_package'))
            db.session.add(self.publisher3)

            db.session.commit()

    def test_publisher_read_is_allowed_if_user_is_owner(self):
        allowed = is_allowed(11, self.publisher, 'Publisher::Read')
        self.assertTrue(allowed)

    def test_publisher_read_is_allowed_if_user_is_member(self):
        allowed = is_allowed(11, self.publisher1, 'Publisher::Read')
        self.assertTrue(allowed)

    def test_publisher_read_is_allowed_if_user_is_sysadmin(self):
        allowed = is_allowed(12, self.publisher, 'Publisher::Read')
        self.assertTrue(allowed)

    def test_publisher_read_is_allowed_if_user_is_anonymous(self):
        allowed = is_allowed(None, self.publisher, 'Publisher::Read')
        self.assertTrue(allowed)

    def test_publisher_read_is_not_allowed_if_user_is_anonymous_and_package_private(self):
        allowed = is_allowed(None, self.publisher2, 'Publisher::Read')
        self.assertFalse(allowed)

    def test_publisher_delete_is_allowed_if_user_is_owner(self):
        allowed = is_allowed(11, self.publisher, 'Publisher::Delete')
        self.assertTrue(allowed)

    def test_publisher_delete_is_allowed_if_user_is_sysadmin(self):
        allowed = is_allowed(12, self.publisher, 'Publisher::Delete')
        self.assertTrue(allowed)

    def test_publisher_delete_is_not_allowed_if_user_is_member(self):
        allowed = is_allowed(11, self.publisher1, 'Publisher::Delete')
        self.assertFalse(allowed)

    def test_publisher_delete_is_not_allowed_if_user_is_anonymous(self):
        allowed = is_allowed(None, self.publisher1, 'Publisher::Delete')
        self.assertFalse(allowed)

    def test_publisher_add_member_is_allowed_if_user_is_owner(self):
        allowed = is_allowed(11, self.publisher, 'Publisher::AddMember')
        self.assertTrue(allowed)

    def test_publisher_add_member_is_allowed_if_user_is_sysadmin(self):
        allowed = is_allowed(12, self.publisher, 'Publisher::AddMember')
        self.assertTrue(allowed)

    def test_publisher_add_member_is_allowed_if_user_is_member(self):
        allowed = is_allowed(11, self.publisher1, 'Publisher::AddMember')
        self.assertTrue(allowed)

    def test_publisher_add_member_is_not_allowed_if_user_is_anonymous(self):
        allowed = is_allowed(None, self.publisher1, 'Publisher::AddMember')
        self.assertFalse(allowed)

    def test_package_read_is_allowed_if_user_is_owner(self):
        package = MetaDataDB.query.join(Publisher)\
            .filter(MetaDataDB.name == 'test_package',
                    Publisher.name == self.publisher.name).one()
        allowed = is_allowed(11, package, 'Package::Read')
        self.assertTrue(allowed)

    def test_package_read_is_allowed_if_user_is_member(self):
        package = MetaDataDB.query.join(Publisher) \
            .filter(MetaDataDB.name == 'test_package',
                    Publisher.name == self.publisher1.name).one()
        allowed = is_allowed(11, package, 'Package::Read')
        self.assertTrue(allowed)

    def test_package_read_is_allowed_if_user_is_sysadmin(self):
        package = MetaDataDB.query.join(Publisher) \
            .filter(MetaDataDB.name == 'test_package',
                    Publisher.name == self.publisher.name).one()
        allowed = is_allowed(12, package, 'Package::Read')
        self.assertTrue(allowed)

    def test_package_read_is_allowed_if_user_is_anonymous(self):
        package = MetaDataDB.query.join(Publisher) \
            .filter(MetaDataDB.name == 'test_package',
                    Publisher.name == self.publisher.name).one()
        allowed = is_allowed(None, package, 'Package::Read')
        self.assertTrue(allowed)

    def test_package_read_is_not_allowed_if_user_is_anonymous_and_package_private(self):
        package = MetaDataDB.query.join(Publisher) \
            .filter(MetaDataDB.name == 'test_package',
                    Publisher.name == self.publisher2.name).one()
        allowed = is_allowed(None, package, 'Package::Read')
        self.assertFalse(allowed)

    def test_package_delete_is_allowed_if_user_is_owner(self):
        package = MetaDataDB.query.join(Publisher) \
            .filter(MetaDataDB.name == 'test_package',
                    Publisher.name == self.publisher.name).one()
        allowed = is_allowed(11, package, 'Package::Purge')
        self.assertTrue(allowed)

    def test_package_delete_is_allowed_if_user_is_sysadmin(self):
        package = MetaDataDB.query.join(Publisher) \
            .filter(MetaDataDB.name == 'test_package',
                    Publisher.name == self.publisher.name).one()
        allowed = is_allowed(12, package, 'Package::Purge')
        self.assertTrue(allowed)

    def test_package_delete_is_not_allowed_if_user_is_member(self):
        package = MetaDataDB.query.join(Publisher) \
            .filter(MetaDataDB.name == 'test_package',
                    Publisher.name == self.publisher1.name).one()
        allowed = is_allowed(11, package, 'Package::Purge')
        self.assertFalse(allowed)

    def test_package_delete_is_not_allowed_if_user_is_anonymous(self):
        package = MetaDataDB.query.join(Publisher) \
            .filter(MetaDataDB.name == 'test_package',
                    Publisher.name == self.publisher.name).one()
        allowed = is_allowed(None, package, 'Package::Purge')
        self.assertFalse(allowed)

    def test_package_add_member_is_allowed_if_user_is_owner(self):
        package = MetaDataDB.query.join(Publisher) \
            .filter(MetaDataDB.name == 'test_package',
                    Publisher.name == self.publisher.name).one()
        allowed = is_allowed(11, package, 'Package::Delete')
        self.assertTrue(allowed)

    def test_package_add_member_is_allowed_if_user_is_sysadmin(self):
        package = MetaDataDB.query.join(Publisher) \
            .filter(MetaDataDB.name == 'test_package',
                    Publisher.name == self.publisher.name).one()
        allowed = is_allowed(12, package, 'Package::Delete')
        self.assertTrue(allowed)

    def test_package_add_member_is_allowed_if_user_is_member(self):
        package = MetaDataDB.query.join(Publisher) \
            .filter(MetaDataDB.name == 'test_package',
                    Publisher.name == self.publisher1.name).one()
        allowed = is_allowed(11, package, 'Package::Delete')
        self.assertTrue(allowed)

    def test_package_add_member_is_not_allowed_if_user_is_anonymous(self):
        package = MetaDataDB.query.join(Publisher) \
            .filter(MetaDataDB.name == 'test_package',
                    Publisher.name == self.publisher1.name).one()
        allowed = is_allowed(None, package, 'Package::Delete')
        self.assertFalse(allowed)

    def test_package_create_is_not_allowed_if_user_is_logged_in(self):
        package = MetaDataDB.query.join(Publisher) \
            .filter(MetaDataDB.name == 'test_package',
                    Publisher.name == self.publisher1.name).one()
        allowed = is_allowed(13, package, 'Package::Create')
        self.assertTrue(allowed)

    def test_publisher_create_is_not_allowed_if_user_is_logged_in(self):
        package = MetaDataDB.query.join(Publisher) \
            .filter(MetaDataDB.name == 'test_package',
                    Publisher.name == self.publisher1.name).one()
        allowed = is_allowed(13, package, 'Publisher::Create')
        self.assertTrue(allowed)

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
