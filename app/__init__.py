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
from flask import Flask, session, request, g
from flask_cors import CORS
from flaskext.markdown import Markdown
from flask_gravatar import Gravatar
from flask_oauthlib.client import OAuth
from werkzeug.utils import import_string
from .database import db
from app.utils import get_s3_cdn_prefix
from app.auth.controllers import auth_blueprint, bitstore_blueprint
from app.auth.models import JWT
from app.package.controllers import package_blueprint
from app.site.controllers import site_blueprint
from app.profile.controllers import profile_blueprint
from app.profile.models import User
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


def get_github_oauth(oauth, client_id, client_secret):
    github = oauth.remote_app(
        'github',
        consumer_key=client_id,
        consumer_secret=client_secret,
        request_token_params={'scope': 'user:email'},
        base_url='https://api.github.com/',
        request_token_url=None,
        access_token_method='POST',
        access_token_url='https://github.com/login/oauth/access_token',
        authorize_url='https://github.com/login/oauth/authorize')
    return github


def create_app():

    app = Flask(__name__)
    app.secret_key = 'dpr-api-secret-key'
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

    oauth = OAuth(app=app)
    CORS(app)
    Swagger(app)
    Markdown(app)
    Gravatar(app)

    github = get_github_oauth(oauth, app.config['GITHUB_CLIENT_ID'],
                              app.config['GITHUB_CLIENT_SECRET'])

    @github.tokengetter
    def get_github_oauth_token():
        return session.get('github_token')

    app.config['github'] = github

    @app.context_processor
    def populate_context_variable():
        return dict(s3_cdn=get_s3_cdn_prefix(),
                    current_user=g.current_user)

    @app.before_request
    def get_user_from_cookie():
        token = request.cookies.get('jwt')
        g.current_user, g.jwt_exception = None, None
        if token:
            try:
                payload = JWT(app.config['API_KEY']).decode(token)
                g.current_user = User().get_userinfo_by_id(payload['user'])
            except Exception as e:
                app.logger.error(e)
                g.jwt_exception = e

    return app
