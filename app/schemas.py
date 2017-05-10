# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

from flask_marshmallow import Marshmallow
from marshmallow import pre_load, pre_dump

from app.package.models import *
from app.profile.models import *
from app.utils import InvalidUsage

ma = Marshmallow()

class PublisherSchema(ma.ModelSchema):
    class Meta:
        model = Publisher
        dateformat = ("%B %Y")

    id = ma.Field(load_only=True)
    created_at = ma.Field(load_only=True)
    phone = ma.Field(load_only=True)
    private = ma.Field(load_only=True)
    country = ma.Field(load_only=True)
    email = ma.Field(load_only=True)
    contact_public = ma.Field(load_only=True)
    users = ma.Field(load_only=True)
    packages = ma.Field(load_only=True)
    contact = ma.Method('add_public_contact')
    joined = ma.DateTime(attribute = 'created_at')

    def add_public_contact(self, data):
        if data.contact_public:
            contact = dict(phone=data.phone,
                           email=data.email,
                           country=data.country)
            return contact

class UserSchema(ma.ModelSchema):
    class Meta:
        model = User


class UserInfoSchema(ma.Schema):
    class Meta:
        fields = ('email', 'login', 'name')

    @pre_load
    def load_user(self, data):
        email = data.get('email')
        emails = data.get('emails')

        if email:
            return data

        if not emails or not len(emails):
            raise InvalidUsage('Email Not Found', 404)

        for email in emails:
            if email.get('primary') == 'true':
                data['email'] = email.get('email')
                return data


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
