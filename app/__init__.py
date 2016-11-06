import os
import flask_s3
from flasgger import Swagger
from flask import Flask
from database import db
from app.mod_api.controllers import mod_api_blueprint
from app.mod_site.controllers import mod_site_blueprint

app_config = {
    "base": "app.config.BaseConfig",
    "test": "app.config.BaseConfig",
    "development": "app.config.DevelopmentConfig",
    "stage": "app.config.StageConfig"
}


def get_config_class_name():
    config_name = os.getenv('FLASK_CONFIGURATION', 'development')
    return app_config[config_name]


def create_app():

    app = Flask(__name__)
    app.config.from_object(get_config_class_name())

    db.init_app(app)

    app.register_blueprint(mod_api_blueprint)
    app.register_blueprint(mod_site_blueprint)

    if app.config.get('TESTING') is False:
        flask_s3.create_all(app)

    Swagger(app)
    return app
