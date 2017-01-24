# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import unittest
from mock import patch
from app import create_app
from app.database import db
from app.profile.models import Publisher


class PublisherProfileTestCase(unittest.TestCase):
    publisher_one = 'test_publisher1'
    publisher_two = 'test_publisher2'

    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()
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

    @patch('app.profile.models.Publisher.get_publisher_info')
    def test_throw_500_if_failed_to_get_data_for_publisher(self, info_mock):
        info_mock.side_effect = Exception
        url = "/api/profile/publisher/{name}".format(name=self.publisher_one)
        response = self.client.get(url)
        self.assertEqual(500, response.status_code)

    @patch('app.profile.models.Publisher.get_publisher_info')
    def test_throw_404_if_publisher_not_found(self, info_mock):
        info_mock.return_value = None
        url = "/api/profile/publisher/{name}".format(name='unknown')
        response = self.client.get(url)
        self.assertEqual(404, response.status_code)

    @patch('app.profile.models.Publisher.get_publisher_info')
    def test_should_return_200_if_every_thing_went_well(self, info_mock):
        info_mock.return_value = {}
        url = "/api/profile/publisher/{name}".format(name=self.publisher_one)
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
