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


class UserTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.app_context().push()
        with self.app.test_request_context():
            db.drop_all()
            db.create_all()

            user = User(id=11,
                        name='test_user_id',
                        secret='supersecret')
            publisher = Publisher(name='test_pub_id')
            association = PublisherUser(role=UserRoleEnum.owner)
            association.publisher = publisher
            user.publishers.append(association)

            db.session.add(user)
            db.session.commit()


    def test_user_role_on_publisher(self):
        user = User.query.filter_by(name='test_user_id').one()
        self.assertEqual(len(user.publishers), 1)
        self.assertEqual(user.publishers[0].role, UserRoleEnum.owner)


    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
