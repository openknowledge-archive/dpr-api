from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand
from flask import current_app, json

from app.database import db
from app.mod_api import models
from app import create_app

migrate = Migrate(create_app(), db)
manager = Manager(create_app())
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
    db.session.add(models.MetaDataDB("demo-package", "demo", data, "avtive", False))
    db.session.commit()

if __name__ == "__main__":
    manager.run()
