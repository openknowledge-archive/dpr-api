# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import sys
import os
import unittest
from app import create_app, get_config_class_name
from app.config import BaseConfig


class BasicTestCase(unittest.TestCase):
    def setUp(self):
        os.putenv('FLASK_CONFIGURATION', 'development')
        self.app = create_app()

    def test_python_version(self):
        """Application runs under Python 2.7, not 2.6.
        Test for 2.7.6 or greater (as long as it's 2.7)."""
        assert 2 == sys.version_info.major
        assert 7 == sys.version_info.minor
        assert 6 <= sys.version_info.micro

    def test_testing_mode(self):
        """Most basic of tests: make sure TESTING = True in app.config."""
        assert self.app.config['TESTING'] is True

    def test_required_config_none(self):
        """All of the required config must not be None"""
        base_config = BaseConfig()
        setattr(base_config, 'required_config', ['TEST_CONF'])
        setattr(base_config, 'TEST_CONF', None)

        self.assertRaises(Exception, base_config.check_required_config)
