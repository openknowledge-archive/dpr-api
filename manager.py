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
from app.mod_api.models import MetaDataDB, Publisher, PublisherUser

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
    readme = open('fixtures/README.md').read()
    user = models.User()
    user.auth0_id, user.email, user.name, user.secret, user.full_name \
        = "auth0|123", "test@gmail.com", "test", \
          "c053521f4f3331908d89df39bba922190a69f0ea99f7ca00", "Test Bob"
    publisher = Publisher(name='demo')

    metadata = MetaDataDB(name="demo-package")
    metadata.descriptor, metadata.status, metadata.private, metadata.readme \
        = json.dumps(data), 'active', False, readme
    publisher.packages.append(metadata)
    association = PublisherUser(role="OWNER")
    association.publisher = publisher
    user.publishers.append(association)

    db.session.add(user)

    db.session.commit()

if __name__ == "__main__":
    manager.run()
