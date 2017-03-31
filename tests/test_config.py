# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import os
import unittest
from app import create_app


class ConfigTestCase(unittest.TestCase):

    def test_prod_config(self):
        os.environ["FLASK_CONFIGURATION"] = "prod"
        os.environ["S3_BUCKET_NAME"] = "test_bucket"
        os.environ["AWS_REGION"] = "us-west-2"
        os.environ["AWS_ACCESS_KEY_ID"] = "access"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "secret"
        os.environ["GITHUB_CLIENT_ID"] = "client_id"
        os.environ["GITHUB_CLIENT_SECRET"] = "client_secret"
        os.environ["SQLALCHEMY_DATABASE_URI"] = "postgresql://@localhost:5432/dpr_db"

        app = create_app()
        self.assertEqual(False, app.config['TESTING'])
        self.assertEqual(False, app.config['DEBUG'])
        self.assertEqual("us-west-2", app.config['AWS_REGION'])

    def test_development_config(self):
        os.environ["FLASK_CONFIGURATION"] = "development"

        os.environ["S3_BUCKET_NAME"] = "test_bucket"
        os.environ["AWS_REGION"] = "us-west-2"
        os.environ["AWS_ACCESS_KEY_ID"] = "access"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "secret"
        os.environ["GITHUB_CLIENT_ID"] = "client_id"
        os.environ["GITHUB_CLIENT_SECRET"] = "client_secret"
        os.environ["SQLALCHEMY_DATABASE_URI"] = "postgresql://@localhost:5432/dpr_db"

        app = create_app()
        self.assertEqual(True, app.config['TESTING'])
        self.assertEqual(True, app.config['DEBUG'])
