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
from werkzeug.exceptions import NotFound, Unauthorized, MethodNotAllowed, BadRequest
from .database import db
from .schemas import ma
from app.auth.controllers import auth_blueprint, bitstore_blueprint
from app.auth.jwt import JWT
from app.logic.db_logic import get_user_by_id
from app.package.controllers import package_blueprint
from app.site.controllers import site_blueprint
from app.profile.controllers import profile_blueprint
from app.profile.models import User
from app.search.controllers import search_blueprint
from app.utils import InvalidUsage
from flask import jsonify

app_config = {
    "base": "app.config.BaseConfig",
    "test": "app.config.BaseConfig",
    "development": "app.config.DevelopmentConfig",
    "stage": "app.config.StageConfig",
    "prod": "app.config.ProductionConfig"
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
    app.config.from_object(get_config_class_name())

    app.secret_key = app.config['JWT_SEED']

    db.init_app(app)
    ma.init_app(app)

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

    oauth = OAuth(app=app)
    CORS(app)
    Swagger(app)
    Markdown(app, safe_mode='escape')
    Gravatar(app)

    github = get_github_oauth(oauth, app.config['GITHUB_CLIENT_ID'],
                              app.config['GITHUB_CLIENT_SECRET'])

    @github.tokengetter
    def get_github_oauth_token():
        return session.get('github_token')

    app.config['github'] = github

    @app.errorhandler(NotFound)
    @app.errorhandler(BadRequest)
    @app.errorhandler(Unauthorized)
    @app.errorhandler(MethodNotAllowed)
    def handle_errors(error):
        response = dict()
        response['status_code'] = error.code
        response['message'] = error.name
        response = jsonify(response)
        app.logger.error(error)
        return response, error.code

    @app.errorhandler(InvalidUsage)
    def handle_costum_error(error):
        response = jsonify(error.to_dict())
        response.status_code = error.status_code
        app.logger.error(error)
        return response

    @app.errorhandler(Exception)
    def handle_internal_error(error):
        response = dict()
        response['status_code'] = 500
        response['message'] = 'Internal Server Error'
        response = jsonify(response)
        app.logger.error(error)
        return response, 500

    @app.context_processor
    def populate_context_variable():
        return dict(current_user=g.current_user)

    @app.before_request
    def get_user_from_cookie():
        token = request.cookies.get('jwt')
        g.current_user = None
        if token:
            payload = JWT(app.config['JWT_SEED']).decode(token)
            g.current_user = get_user_by_id(payload['user'])

    return app
