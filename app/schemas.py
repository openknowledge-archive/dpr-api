# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

from flask_marshmallow import Marshmallow
from app.package.models import *
from app.profile.models import *

ma = Marshmallow()

class PublisherSchema(ma.ModelSchema):
    class Meta:
        model = Publisher


class UserSchema(ma.ModelSchema):
    class Meta:
        model = User


class PublisherUserSchema(ma.ModelSchema):
    class Meta:
        model = PublisherUser


class PackageSchema(ma.ModelSchema):
    class Meta:
        model = Package


class PackageTagSchema(ma.ModelSchema):
    class Meta:
        model = PackageTag


class PackageMetadataSchema(ma.Schema):
    class Meta:
        fields = ('id', 'name', 'publisher', 'readme', 'descriptor')

    publisher = ma.Method('get_publisher_name')
    readme = ma.Method('get_readme')
    descriptor = ma.Method('get_descriptor')

    def get_publisher_name(self, data):
        return data.publisher.name

    def get_readme(self, data):
        version = filter(lambda t: t.tag == 'latest', data.tags)[0]
        return version.readme or ''

    def get_descriptor(self, data):
        version = filter(lambda t: t.tag == 'latest', data.tags)[0]
        return version.descriptor
