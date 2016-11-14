# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import os
from os.path import join, dirname
from dotenv import load_dotenv


class BaseConfig(object):
    required_config = ['AWS_REGION', 'SQLALCHEMY_DATABASE_URI',
                       'S3_BUCKET_NAME', 'FLASKS3_BUCKET_NAME']

    API_KEY = "dpr-api-key"
    DEBUG = True
    TESTING = True
    SWAGGER = {
        "swagger_version": "2.0",
        "title": "DPR API",
        "specs": [
            {
                "version": "0.0.1",
                "title": "v1",
                "endpoint": 'spec',
                "description": "First Cut for DPR API",
                "route": '/spec',
                "rule_filter": lambda rule: True
            }
        ]
    }
    AWS_ACCESS_KEY_ID = ""
    AWS_SECRET_ACCESS_KEY = ""
    AWS_REGION = "eu-west-1"

    AUTH0_CLIENT_ID = ""
    AUTH0_CLIENT_SECRET = ""
    AUTH0_DOMAIN = ""
    AUTH0_DB_NAME = ""
    AUTH0_CALLBACK_URL = ""
    AUTH0_API_AUDIENCE = ""

    SQLALCHEMY_DATABASE_URI = 'postgresql://@localhost/dpr_db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    S3_BUCKET_NAME = "test"

    FLASKS3_BUCKET_NAME = "test"
    FLASKS3_FILEPATH_HEADERS = {
        r'/*\.css': {'Content-Type': 'text/css'},
        r'/*\.js': {'Content-Type': "text/javascript"}
    }

    def check_required_config(self):
        for conf in self.required_config:
            conf_value = self.__getattribute__(conf)
            if conf_value is None:
                raise Exception("value of %s can not be None" % conf)


class DevelopmentConfig(BaseConfig):
    required_config = ['AWS_REGION', 'S3_BUCKET_NAME',
                       'FLASKS3_BUCKET_NAME', 'AWS_ACCESS_KEY_ID',
                       'AWS_SECRET_ACCESS_KEY', 'AUTH0_CLIENT_ID',
                       'AUTH0_CLIENT_SECRET', 'AUTH0_DOMAIN',
                       'AUTH0_DB_NAME', 'AUTH0_CALLBACK_URL',
                       'AUTH0_API_AUDIENCE', 'SQLALCHEMY_DATABASE_URI',
                       'S3_BUCKET_NAME', 'FLASKS3_BUCKET_NAME']
    try:
        dot_env_path = join(dirname(__file__), '../.env')
        load_dotenv(dot_env_path)
    except Exception as e:
        pass

    DEBUG = True
    TESTING = True
    # need to add as test would fail
    S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME')
    FLASKS3_BUCKET_NAME = os.environ.get('FLASKS3_BUCKET_NAME')
    FLASKS3_REGION = os.environ.get('AWS_REGION')

    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    AWS_REGION = os.environ.get('AWS_REGION')

    AUTH0_CLIENT_ID = os.environ.get('AUTH0_CLIENT_ID')
    AUTH0_CLIENT_SECRET = os.environ.get('AUTH0_CLIENT_SECRET')
    AUTH0_DOMAIN = os.environ.get('AUTH0_DOMAIN')
    AUTH0_DB_NAME = os.environ.get('AUTH0_DB_NAME')
    AUTH0_CALLBACK_URL = os.environ.get('AUTH0_CALLBACK_URL')
    AUTH0_API_AUDIENCE = os.environ.get('AUTH0_API_AUDIENCE')

    SQLALCHEMY_DATABASE_URI = os.environ.get("SQLALCHEMY_DATABASE_URI")


class StageConfig(DevelopmentConfig):
    DEBUG = False
    TESTING = False
