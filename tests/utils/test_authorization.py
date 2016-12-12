# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import unittest
from app.database import db
from app import create_app
from app.utils.authorization import get_roles, roles
from app.mod_api.models import MetaDataDB, User, Publisher, \
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
            self.sysadmin = User(id=12,
                                 name='admin',
                                 sysadmin=True)
            self.publisher = Publisher(name=self.user_name)
            self.publisher.packages.append(MetaDataDB(name='test_package'))

            self.publisher1 = Publisher(name="test_publisher")
            self.publisher1.packages.append(MetaDataDB(name='test_package'))

            association = PublisherUser(role=UserRoleEnum.owner)
            association.publisher = self.publisher
            self.user.publishers.append(association)

            association1 = PublisherUser(role=UserRoleEnum.member)
            association1.publisher = self.publisher1
            self.user.publishers.append(association1)

            db.session.add(self.user)
            db.session.add(self.sysadmin)

            self.publisher2 = Publisher(name="test_publisher1", private=True)
            self.publisher2.packages.append(MetaDataDB(name='test_package'))
            db.session.add(self.publisher2)

            self.publisher3 = Publisher(name="test_publisher2", private=False)
            self.publisher3.packages.append(MetaDataDB(name='test_package'))
            db.session.add(self.publisher3)

            db.session.commit()

    def test_should_return_anonymous_roles_if_user_id_is_none_and_entity_is_public(self):
        anonymous_roles = get_roles(None, self.publisher1)
        self.assertEqual(anonymous_roles, roles['System']['Anonymous'])

    def test_should_return_blank_roles_if_user_id_is_none_and_entity_is_private(self):
        anonymous_roles = get_roles(None, self.publisher2)
        self.assertEqual(anonymous_roles, [])

    def test_sys_admin_roles(self):
        sysadmin_roles = get_roles(12, None)
        self.assertEqual(sysadmin_roles, roles['System']['Sysadmin'])

    def test_publisher_owner_roles(self):
        publisher_roles = get_roles(11, self.publisher)
        self.assertEqual(publisher_roles, roles['Publisher']['Owner'])

    def test_publisher_member_roles(self):
        publisher_roles = get_roles(11, self.publisher1)
        self.assertEqual(publisher_roles, roles['Publisher']['Editor'])

    def test_publisher_viewer_roles_for_private(self):
        publisher_roles = get_roles(11, self.publisher2)
        self.assertEqual(publisher_roles, roles['System']['LoggedIn'])

    def test_publisher_viewer_roles_for_public(self):
        publisher_roles = get_roles(11, self.publisher3)
        self.assertEqual(publisher_roles, roles['System']['LoggedIn'] +
                         roles['Publisher']['Viewer'])

    def test_should_return_logged_in_roles_if_publisher_is_None(self):
        publisher_roles = get_roles(11, None)
        self.assertEqual(publisher_roles, roles['System']['LoggedIn'])

    def test_should_return_logged_in_roles_if_package_is_None(self):
        package_roles = get_roles(11, None)
        self.assertEqual(package_roles, roles['System']['LoggedIn'])

    def test_should_return_package_owner_roles_if_user_is_owner_of_package(self):
        instance = MetaDataDB.get_package(self.publisher.name, 'test_package')
        package_roles = get_roles(11, instance)
        self.assertEqual(package_roles, roles['Package']['Owner'])

    def test_should_return_package_editor_roles_if_user_is_member_of_package(self):
        instance = MetaDataDB.get_package(self.publisher1.name, 'test_package')
        package_roles = get_roles(11, instance)
        self.assertEqual(package_roles, roles['Package']['Editor'])

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
