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
from app.package import models
from app import create_app
from app.package.models import Package, Publisher, \
    PublisherUser, User, BitStore, UserRoleEnum
from app.auth.models import Auth0

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
    user_name, full_name, email = 'core', 'Test Admin', 'core@test.com'
    auth0_id = populate_auth0(user_name, full_name, email)
    populate_db(auth0_id, email, user_name, full_name,
                'c053521f4f3331908d89df39bba922190a69f0ea99f7ca12')

    user_name, full_name, email = 'admin', 'Test Admin', 'test@test.com'
    auth0_id = populate_auth0(user_name, full_name, email)
    populate_db(auth0_id, email, user_name, full_name,
                'c053521f4f3331908d89df39bba922190a69f0ea99f7ca00')
    populate_data(user_name)


def populate_auth0(user_name, full_name, email):
    auth0 = Auth0()
    responses = auth0.search_user('username', user_name)
    if len(responses) > 0:
        for response in responses:
            auth0.delete_user(response['user_id'])
    user_create = auth0.create_user(email, full_name,
                                    user_name, 'Admin123')
    return user_create['user_id']


def populate_db(auth0_id, email, user_name, full_name, secret):
    user = User.query.filter_by(name=user_name).first()

    publisher = Publisher.query.filter_by(name=user_name).first()
    if user is None:
        user = User()
        user.auth0_id, user.email, user.name, user.full_name, user.secret \
            = auth0_id, email, user_name, full_name, secret
        db.session.add(user)
        db.session.commit()

    if publisher is None:

        publisher = Publisher(name=user_name)

        association = PublisherUser(role=UserRoleEnum.owner)
        association.publisher = publisher
        user.publishers.append(association)

        db.session.add(user)
        db.session.commit()


def populate_data(publisher_name):
    data = json.loads(open('fixtures/datapackage.json').read())
    data_csv = open('fixtures/data/demo-resource.csv').read()
    readme = open('fixtures/README.md').read()
    package = Package.query.join(Publisher)\
        .filter(Package.name == "demo-package",
                Publisher.name == publisher_name).first()
    if package:
        db.session.delete(Package.query.get(package.id))
        db.session.commit()
    publisher = Publisher.query.filter_by(name=publisher_name).first()
    metadata = Package(name="demo-package")
    metadata.descriptor, metadata.status, metadata.private, metadata.readme \
        = json.dumps(data), 'active', False, readme

    publisher.packages.append(metadata)
    db.session.add(publisher)
    db.session.commit()
    bitstore = BitStore(publisher_name, package='demo-package', body=json.dumps(data))
    bitstore.save_metadata()
    key = bitstore.build_s3_key('demo-resource.csv')
    bucket_name = app.config['S3_BUCKET_NAME']
    s3_client = app.config['S3']
    s3_client.put_object(Bucket=bucket_name, Key=key, Body=data_csv, ACL='public-read')

if __name__ == "__main__":
    manager.run()
