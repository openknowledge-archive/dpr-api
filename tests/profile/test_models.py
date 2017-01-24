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
        self.app = create_app()
        self.app.app_context().push()

    def test_throw_error_if_role_is_invalid(self):
        with self.app.test_request_context():
            db.drop_all()
            db.create_all()
            publisher = Publisher(name='test_pub_id')
            association = PublisherUser()
            association.publisher = publisher
            self.assertRaises(ValueError, association.role, "NOT_MEMBER")

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()


class PublisherTestCase(unittest.TestCase):
    publisher_one = 'test_publisher1'
    publisher_two = 'test_publisher2'

    def setUp(self):
        self.app = create_app()
        self.app.app_context().push()
        with self.app.test_request_context():
            db.drop_all()
            db.create_all()
            publisher1 = Publisher(name=self.publisher_one,
                                   title="publisher one",
                                   description="This is publisher one",
                                   country="country one",
                                   email="one@publisher.com",
                                   phone="123",
                                   contact_public=True)
            publisher2 = Publisher(name=self.publisher_two,
                                   title="publisher two",
                                   description="This is publisher two",
                                   country="country two",
                                   email="two@publisher.com",
                                   phone="321",
                                   contact_public=False)
            db.session.add(publisher1)
            db.session.add(publisher2)
            db.session.commit()

    def test_should_not_return_contact_info_if_public(self):
        info = Publisher.get_publisher_info(self.publisher_two)
        self.assertNotIn("contact", info)
        self.assertEqual(self.publisher_two, info['name'])

    def test_should_return_contact_info_if_public(self):
        info = Publisher.get_publisher_info(self.publisher_one)
        self.assertIn("contact", info)
        self.assertEqual(self.publisher_one, info['name'])

    def test_should_return_None_if_publisher_not_found(self):
        info = Publisher.get_publisher_info("not_found")
        self.assertIsNone(info)

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()


class UserTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.app_context().push()
        with self.app.test_request_context():
            db.drop_all()
            db.create_all()

            user = User(id=11,
                        name='test_user_id',
                        secret='supersecret',
                        auth0_id="123|auth0")
            publisher = Publisher(name='test_pub_id')
            association = PublisherUser(role=UserRoleEnum.owner)
            association.publisher = publisher
            user.publishers.append(association)

            db.session.add(user)
            db.session.commit()

    def test_serialize(self):
        user = User.query.filter_by(name='test_user_id').one() \
            .serialize
        self.assertEqual('test_user_id', user['name'])

    def test_user_role_on_publisher(self):
        user = User.query.filter_by(name='test_user_id').one()
        self.assertEqual(len(user.publishers), 1)
        self.assertEqual(user.publishers[0].role, UserRoleEnum.owner)

    def test_user_creation_from_outh0_response(self):
        user_info = dict(email="test@test.com",
                         username="test",
                         user_id="124|auth0")
        user = User.create_or_update_user_from_callback(user_info)
        self.assertEqual(user.name, 'test')

    def test_update_secret_if_it_is_supersecret(self):
        user_info = dict(email="test@test.com",
                         username="test",
                         user_id="123|auth0")
        user = User.create_or_update_user_from_callback(user_info)
        self.assertNotEqual('supersecret', user.secret)

    def test_get_userinfo_by_id(self):
        self.assertEqual(User.get_userinfo_by_id(11).name, 'test_user_id')
        self.assertIsNone(User.get_userinfo_by_id(2))

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()