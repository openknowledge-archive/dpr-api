# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import unittest
from app import create_app
from moto import mock_s3
from app.auth.jwt import FileData


class FileDataTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()

    def test_should_throw_error_if_name_is_None(self):
        with self.app.app_context():
            file_data = FileData(package_name='abc',
                                 publisher='pub',
                                 relative_path="data/readme.md",
                                 props={'md5': 'as131twfc56t7',
                                        'type': 'json'})
            self.assertRaises(file_data)

    @mock_s3
    def test_should_return_upload_url(self):
        with self.app.app_context():
            file_data = FileData(package_name='abc',
                                 publisher='pub',
                                 relative_path="data/readme.md",
                                 props={'md5': 'as131twfc56t7',
                                        'type': 'json',
                                        'name': 'readme.md'})
            response = file_data.build_file_information()
            self.assertIsNotNone(response['upload_url'])