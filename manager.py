# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand
from flask import current_app, json
from os.path import join, dirname
from dotenv import load_dotenv
from app.database import db
from app.mod_api import models
from app import create_app
from app.mod_api.models import MetaDataDB

dot_env_path = join(dirname(__file__), '.env')
load_dotenv(dot_env_path)

app = create_app()
manager = Manager(app)

migrate = Migrate(app, db)
manager.add_command('db', MigrateCommand)


def _make_context():
    return dict(app=current_app, db=db, models=models)

    manager.add_option('-c', '--config', dest='config', required=False)


@manager.command
def createdb():
    db.init_app(current_app)
    db.create_all()


@manager.command
def dropdb():
    db.init_app(current_app)
    db.drop_all()


@manager.command
def populate():
    data = json.loads(open('fixtures/datapackage.json').read())
    metadata = MetaDataDB("finance-vix", "demo")
    metadata.descriptor, metadata.status, metadata.private \
        = json.dumps(data), 'active', False
    db.session.add(metadata)
    user = models.User()
    user.user_id, user.email, user.user_name, user.secret \
        = "auth0|123", "test@gmail.com", "test", "secret"

    db.session.add(user)
    db.session.commit()

if __name__ == "__main__":
    manager.run()
