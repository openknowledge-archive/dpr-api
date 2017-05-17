# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import unittest
from app import create_app
from app.database import db
from app.profile.models import User, Publisher, UserRoleEnum, PublisherUser


class PublisherUserTestCase(unittest.TestCase):

    def setUp(self):
        self.publisher = 'demo'
        self.app = create_app()
        self.app.app_context().push()
        with self.app.test_request_context():
            db.drop_all()
            db.create_all()

            user = User(name=self.publisher)
            publisher = Publisher(name=self.publisher)
            association = PublisherUser(role=UserRoleEnum.owner)
            association.publisher = publisher
            user.publishers.append(association)

            db.session.add(user)
            db.session.commit()


    def test_throw_error_if_role_is_invalid(self):
        with self.app.test_request_context():
            db.drop_all()
            db.create_all()
            publisher = Publisher(name='test_pub_id')
            association = PublisherUser()
            association.publisher = publisher
            self.assertRaises(ValueError, association.role, "NOT_MEMBER")

    def test_get_by_name(self):
        pub = Publisher.get_by_name(self.publisher)
        self.assertEqual(pub.name, self.publisher)

    def test_get_by_name_returns_none_if_no_publisher(self):
        pub = Publisher.get_by_name('not_a_publisher')
        self.assertIsNone(pub)


    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()


class UserTestCase(unittest.TestCase):
    def setUp(self):
        self.user_name = 'demo'
        self.app = create_app()
        self.app.app_context().push()
        with self.app.test_request_context():
            db.drop_all()
            db.create_all()

            user = User(id=11,
                        name=self.user_name,
                        secret='supersecret')
            publisher = Publisher(name='test_pub_id')
            association = PublisherUser(role=UserRoleEnum.owner)
            association.publisher = publisher
            user.publishers.append(association)

            db.session.add(user)
            db.session.commit()


    def test_user_role_on_publisher(self):
        user = User.query.filter_by(name=self.user_name).one()
        self.assertEqual(len(user.publishers), 1)
        self.assertEqual(user.publishers[0].role, UserRoleEnum.owner)

    def test_get_by_name(self):
        usr = User.get_by_name(self.user_name)
        self.assertEqual(usr.name, self.user_name)

    def test_get_by_name_returns_none_if_no_user(self):
        usr = User.get_by_name('not_a_user')
        self.assertIsNone(usr)

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
