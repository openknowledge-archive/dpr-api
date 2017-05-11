# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import os
from os.path import join, dirname
from dotenv import load_dotenv


class BaseConfig(object):
    required_config = ['AWS_REGION', 'SQLALCHEMY_DATABASE_URI',
                       'S3_BUCKET_NAME',
                       'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY',
                       "GITHUB_CLIENT_ID", 'GITHUB_CLIENT_SECRET']

    DOMAIN = "datapackaged.com"
    JWT_SEED = "dpr-api-key"
    DEBUG = True
    TESTING = True
    API_DOCS = '/apidocs/index.html'
    SWAGGER = {
        "swagger_version": "2.0",
        "title": "DataHub API",
        "specs": [
            {
                "title": "v0.5",
                "endpoint": 'spec',
                "route": '/api/swagger.json',
                "rule_filter": lambda rule: True
            }
        ]
    }
    AWS_REGION = "eu-west-1"
    AWS_ACCESS_KEY_ID = ""
    AWS_SECRET_ACCESS_KEY = ""

    GITHUB_CLIENT_ID = 'id'
    GITHUB_CLIENT_SECRET = 'secret'

    SQLALCHEMY_DATABASE_URI = 'postgresql://dpr_user:secret@localhost/dpr_db_test'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    S3_BUCKET_NAME = "test"
    BITSTORE_URL = 'https://bits.' + DOMAIN

    FRONT_PAGE_SHOWCASE_PACKAGES = [
        {"publisher": "core", "package": "s-and-p-500-companies"},
        {"publisher": "core", "package": "house-prices-us"},
        {"publisher": "core", "package": "gold-prices"}
    ]

    TUTORIAL_PACKAGES = [
        {"publisher": "examples", "package": "simple-graph-spec"},
        {"publisher": "examples", "package": "vega-views-tutorial-topojson"},
        {"publisher": "examples", "package": "geojson-tutorial"}
    ]

    def check_required_config(self):
        for conf in self.required_config:
            conf_value = self.__getattribute__(conf)
            if conf_value is None:
                raise Exception("value of %s can not be None" % conf)


class DevelopmentConfig(BaseConfig):
    required_config = ['S3_BUCKET_NAME',
                       'AWS_REGION', 'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY',
                       'GITHUB_CLIENT_ID', 'GITHUB_CLIENT_SECRET',
                       'SQLALCHEMY_DATABASE_URI']
    try:
        dot_env_path = join(dirname(__file__), '../.env')
        load_dotenv(dot_env_path)
    except Exception as e:
        pass

    DEBUG = True
    TESTING = True

    JWT_SEED = os.environ.get("JWT_SEED")

    # need to add as test would fail
    S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME')
    FLASKS3_REGION = os.environ.get('AWS_REGION')

    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    AWS_REGION = os.environ.get('AWS_REGION')

    GITHUB_CLIENT_ID = os.environ.get('GITHUB_CLIENT_ID')
    GITHUB_CLIENT_SECRET = os.environ.get('GITHUB_CLIENT_SECRET')

    SQLALCHEMY_DATABASE_URI = os.environ.get("SQLALCHEMY_DATABASE_URI")


class StageConfig(DevelopmentConfig):

    required_config = ['S3_BUCKET_NAME', 'JWT_SEED',
                       'AWS_REGION', 'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY',
                       'GITHUB_CLIENT_ID', 'GITHUB_CLIENT_SECRET',
                       'SQLALCHEMY_DATABASE_URI']
    API_DOCS = 'https://docs.datapackaged.com/developers/api/'
    BITSTORE_URL = os.environ.get('BITSTORE_URL')
    DEBUG = False
    TESTING = False


class ProductionConfig(StageConfig):
    TESTING = False
    DEBUG = False
