# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import os
import flask_s3
import boto3
import sqlalchemy
from botocore.client import Config
from flasgger import Swagger
from flask import Flask
from flask_cors import CORS
from flaskext.markdown import Markdown
from flask_gravatar import Gravatar
from werkzeug.utils import import_string
from .database import db
from app.utils import get_s3_cdn_prefix
from app.auth.controllers import auth_blueprint, bitstore_blueprint
from app.package.controllers import package_blueprint
from app.site.controllers import site_blueprint
from app.profile.controllers import profile_blueprint
from app.search.controllers import search_blueprint

app_config = {
    "base": "app.config.BaseConfig",
    "test": "app.config.BaseConfig",
    "development": "app.config.DevelopmentConfig",
    "stage": "app.config.StageConfig"
}


def get_config_class_name():
    config_name = os.getenv('FLASK_CONFIGURATION', 'development')
    class_name = app_config[config_name]
    config_class = import_string(class_name)()
    getattr(config_class, 'check_required_config')()
    return class_name


def create_app():

    app = Flask(__name__)
    app.config.from_object(get_config_class_name())

    db.init_app(app)
    
    try:
        # Check connection using database url from config.
        engine = sqlalchemy.create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
        engine.connect()
    except Exception as e:
        raise Exception(
            "Failed to connect to the database `%s`.\n"
            "Please set valid uri in the SQLALCHEMY_DATABASE_URI config variable.\n"
            "Original error was:\n"
            "  %s\n" % (app.config['SQLALCHEMY_DATABASE_URI'], str(e)))

    app.register_blueprint(package_blueprint)
    app.register_blueprint(auth_blueprint)
    app.register_blueprint(site_blueprint)
    app.register_blueprint(profile_blueprint)
    app.register_blueprint(search_blueprint)
    app.register_blueprint(bitstore_blueprint)

    s3 = boto3.client('s3',
                      region_name=app.config['AWS_REGION'],
                      aws_access_key_id=app.config['AWS_ACCESS_KEY_ID'],
                      config=Config(signature_version='s3v4'),
                      aws_secret_access_key=app.config['AWS_SECRET_ACCESS_KEY']
                      )
    app.config['S3'] = s3

    if app.config.get('TESTING') is False:
        flask_s3.create_all(app)

    CORS(app)
    Swagger(app)
    Markdown(app)
    Gravatar(app)

    @app.context_processor
    def populate_context_variable():
        return dict(s3_cdn=get_s3_cdn_prefix(),
                    auth0_client_id=app.config['AUTH0_CLIENT_ID'],
                    auth0_domain=app.config['AUTH0_DOMAIN'])

    return app
