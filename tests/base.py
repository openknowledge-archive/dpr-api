import unittest

from app import create_app
from app.database import db
from app.profile.models import User, Publisher, PublisherUser, UserRoleEnum
from app.package.models import Package


def make_fixtures(app, package, publisher, user_id):
    with app.app_context():
        user = User()
        user.id = user_id
        user.email, user.name, user.secret = \
            'test@test.com', publisher, 'super_secret'
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


class TestBase(unittest.TestCase):
    pass

