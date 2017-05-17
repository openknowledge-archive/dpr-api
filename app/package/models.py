# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import json
import datetime

import enum
from sqlalchemy import ForeignKey
from sqlalchemy import UniqueConstraint
from flask import current_app as app
from sqlalchemy.orm import relationship
from app.profile.models import Publisher
from app.database import db
from botocore.exceptions import ClientError


class PackageStateEnum(enum.Enum):
    active = "ACTIVE"
    deleted = "DELETED"


class Package(db.Model):
    """
    This class is DB model for storing package data
    """
    __tablename__ = "package"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    name = db.Column(db.TEXT, index=True)
    status = db.Column(db.Enum(PackageStateEnum, native_enum=False),
                       index=True, default=PackageStateEnum.active)
    private = db.Column(db.BOOLEAN, default=False)

    publisher_id = db.Column(db.Integer, ForeignKey('publisher.id', ondelete='CASCADE'))
    publisher = relationship("Publisher", back_populates="packages",
                             cascade="save-update, merge, delete, delete-orphan",
                             single_parent=True)

    tags = relationship("PackageTag", back_populates="package")

    __table_args__ = (
        UniqueConstraint("name", "publisher_id"),
    )

    @classmethod
    def get_by_publisher(cls, publisher_name, package_name):
        instance = cls.query.join(Publisher) \
            .filter(Package.name == package_name,
                    Publisher.name == publisher_name).one_or_none()
        return instance


class PackageTag(db.Model):

    __tablename__ = 'package_tag'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    tag = db.Column(db.TEXT, index=True, default='latest')
    tag_description = db.Column(db.Text)

    descriptor = db.Column(db.JSON)
    readme = db.Column(db.TEXT)

    package_id = db.Column(db.Integer, ForeignKey("package.id", ondelete='CASCADE'))

    package = relationship("Package", back_populates="tags",
                           cascade="save-update, merge, delete, delete-orphan",
                           single_parent=True)

    __table_args__ = (
        UniqueConstraint("tag", "package_id"),
    )
