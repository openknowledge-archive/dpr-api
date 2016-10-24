import os
from flasgger import Swagger
from flask import Flask
from database import db
from os.path import join, dirname
from dotenv import load_dotenv
from app.mod_api.controllers import mod_api
from app.mod_site.controllers import mod_site

app_config = {
    "development": "app.config.DevelopmentConfig",
    "default": "app.config.DevelopmentConfig"
}


def get_config_class_name():
    config_name = os.getenv('FLASK_CONFIGURATION', 'default')
    return app_config[config_name]


def create_app():
    dot_env_path = join(dirname(__file__), '../.env')
    load_dotenv(dot_env_path)

    app = Flask(__name__)
    app.config.from_object(get_config_class_name())

    db.init_app(app)

    app.register_blueprint(mod_api)
    app.register_blueprint(mod_site)

    Swagger(app)
    return app
