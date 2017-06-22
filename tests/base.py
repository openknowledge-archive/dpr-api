import unittest

from app import create_app
from app.database import db
from app.profile.models import User, Publisher, PublisherUser, UserRoleEnum
from app.package.models import Package
import app.logic as logic


def make_fixtures(app, package, publisher, user_id):
    with app.app_context():
        user = User(
                id=user_id,
                email='test@test.com',
                name=publisher,
                secret='super_secret'
                )
        pub = Publisher(name=publisher)
        pub.packages.append(Package(name=package))
        association = PublisherUser(role=UserRoleEnum.owner)
        association.publisher = pub
        user.publishers.append(association)

        user1 = User(id=2, name='test1',
                     secret='super_secret1', email="test1@test.com")
        pub1 = Publisher(name='test1')
        association1 = PublisherUser(role=UserRoleEnum.owner)
        association1.publisher = pub1
        user1.publishers.append(association1)

        db.session.add(user)
        db.session.add(user1)
        db.session.commit()

def create_test_package(publisher='demo', package='demo-package', descriptor={}, readme=''):
    user = User(name=publisher, secret='supersecret', email='test@test.com')
    publisher = Publisher(name=publisher)
    association = PublisherUser(role=UserRoleEnum.owner)
    association.publisher = publisher
    user.publishers.append(association)

    package = Package(name=package, descriptor=descriptor, readme=readme)
    publisher.packages.append(package)

    db.session.add(user)
    db.session.commit()

def get_valid_token(username):
    user = User.query.filter_by(name=username).one()
    return logic.get_jwt_token(secret=user.secret, username=username)


class TestBase(unittest.TestCase):
    def setup_class(self):
        db.drop_all()
        db.create_all()
        create_test_package()

