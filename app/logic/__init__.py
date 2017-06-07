# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import json
import os

from BeautifulSoup import BeautifulSoup
from flask import request, session
from flask import current_app as app
from sqlalchemy.orm.exc import NoResultFound

from app.auth.annotations import check_is_authorized, get_user_from_jwt
from app.auth.jwt import JWT, FileData
from app.database import db
from app.bitstore import BitStore
from app.logic.search import DataPackageQuery
from app.utils import InvalidUsage
from app.utils.helpers import text_to_markdown, dp_in_readme
import app.models as models


from flask_marshmallow import Marshmallow
from marshmallow import pre_load, pre_dump
from marshmallow_enum import EnumField


ma = Marshmallow()


class LogicBase(object):

    schema = None

    @classmethod
    def serialize(cls, sqla_instance):
        if sqla_instance is None:
            return None
        serialized = cls.schema().dump(sqla_instance).data
        return serialized

    @classmethod
    def deserialize(cls, dict_object):
        deserialized = cls.schema().load(dict_object, session=db.session).data
        return deserialized


#####################################################
# Packages

class PackageSchema(ma.ModelSchema):
    class Meta:
        model = models.Package

    status = EnumField(models.PackageStateEnum)


class PackageTagSchema(ma.ModelSchema):
    class Meta:
        model = models.PackageTag




class PackageMetadataSchema(ma.Schema):
    class Meta:
        fields = ('id', 'name', 'publisher', 'readme',
            'descriptor', 'bitstore_url', 'short_readme')

    publisher = ma.Method('get_publisher_name')
    readme = ma.Method('get_readme')
    descriptor = ma.Method('get_descriptor')
    bitstore_url = ma.Method('get_url')
    short_readme = ma.Method('get_short_readme')


    def get_publisher_name(self, data):
        return data.publisher.name

    def get_readme(self, data):
        readme_variables_replaced = dp_in_readme(data.readme or '', data.descriptor)
        readme = text_to_markdown(readme_variables_replaced)
        return readme

    def get_descriptor(self, data):
        descriptor = validate_for_template(data.descriptor)
        descriptor['owner'] = data.publisher.name
        return data.descriptor

    def get_url(self, data):
        bitstore = BitStore(data.publisher.name, data.name)
        datapackage_json_url_in_s3 = bitstore.build_s3_object_url()
        return datapackage_json_url_in_s3

    def get_short_readme(self, data):
        readme_short_markdown = text_to_markdown(data.readme or '')
        readme_short = ''.join(BeautifulSoup(readme_short_markdown).findAll(text=True)) \
            .split('\n\n')[0].replace(' \n', '') \
            .replace('\n', ' ').replace('/^ /', '')
        return readme_short


class Package(LogicBase):
    schema = PackageMetadataSchema

    @classmethod
    def get(cls, publisher, package):
        data = models.Package.get_by_publisher(publisher, package)
        return cls.serialize(data)

    @classmethod
    def exists(cls, publisher, package):
        instance = models.Package.get_by_publisher(publisher, package)
        return instance is not None

    @classmethod
    def delete(cls, publisher, package):
        pkg = models.Package.get_by_publisher(publisher, package)
        # TODO: should be able to db.session.delete(pkg) but deletes publishers!
        models.Package.query.filter(models.Package.id == pkg.id).delete()
        db.session.commit()
        return True

    @classmethod
    def create_or_update_tag(cls, publisher, package, tag):
        package = models.Package.get_by_publisher(publisher, package)

        data_latest = models.PackageTag.query.join(models.Package)\
            .filter(models.Package.id == package.id,
                    models.PackageTag.tag == 'latest').one()

        tag_instance = models.PackageTag.query.join(models.Package) \
            .filter(models.Package.id == package.id,
                    models.PackageTag.tag == tag).first()

        update_props = ['descriptor', 'readme', 'package_id']
        if tag_instance is None:
            tag_instance = models.PackageTag()

        for update_prop in update_props:
            setattr(tag_instance, update_prop, getattr(data_latest, update_prop))
        tag_instance.tag = tag

        db.session.add(tag_instance)
        db.session.commit()
        return True

    @classmethod
    def create_or_update(cls, name, publisher_name, **kwargs):
        pub_id = models.Publisher.query.filter_by(name=publisher_name).one().id
        instance = models.Package.get_by_publisher(publisher_name, name)

        if instance is None:
            instance = models.Package(name=name)
            instance.publisher_id = pub_id

        for key, value in kwargs.items():
            setattr(instance, key, value)

        db.session.add(instance)
        db.session.commit()

    @classmethod
    def change_status(cls, publisher_name,
                            package_name, status=models.PackageStateEnum.active):
        pkg = models.Package.get_by_publisher(publisher_name, package_name)
        pkg.status = status
        db.session.add(pkg)
        db.session.commit()
        return True

    @classmethod
    def finalize_publish(cls, user_id, datapackage_url):
        '''
        Gets the datapackage.json and README from S3 and imports into database.
        Returns status "queued" if ok, else - None
        '''
        publisher, package, version = BitStore.extract_information_from_s3_url(datapackage_url)
        if Package.exists(publisher, package):
            status = check_is_authorized('Package::Update', publisher, package, user_id)
        else:
            status = check_is_authorized('Package::Create', publisher, package, user_id)

        if not status:
            raise InvalidUsage('Not authorized to upload data', 400)

        bit_store = BitStore(publisher, package)
        b = bit_store.get_metadata_body()
        body = json.loads(b)
        bit_store.change_acl('public-read')
        readme = bit_store.get_s3_object(bit_store.get_readme_object_key())
        Package.create_or_update(name=package, publisher_name=publisher,
                                 descriptor=body, readme=readme)
        return "queued"


class PackageTag(LogicBase):
    schema = PackageTagSchema

    @classmethod
    def get(cls, package_id, tag):
        tag = models.PackageTag.get_by_tag(package_id, tag)
        return cls.serialize(tag)

#####################################################
# Profiles - Publishers and Users

class PublisherSchema(ma.ModelSchema):
    class Meta:
        model = models.Publisher
        dateformat = ("%B %Y")

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
        model = models.User


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
        model = models.PublisherUser

    role = EnumField(models.UserRoleEnum)


class Publisher(LogicBase):

    schema = PublisherSchema

    @classmethod
    def get(cls, publisher):
        pub = models.Publisher.get_by_name(publisher)
        return cls.serialize(pub)

    @classmethod
    def create(cls, metadata):
        pub = cls.deserialize(metadata)
        db.session.add(pub)
        db.session.commit()
        return pub

class User(LogicBase):

    schema = UserSchema

    @classmethod
    def get(cls, usr_id):
        usr = models.User.query.get(usr_id)
        return cls.serialize(usr)

    @classmethod
    def create(cls, metadata):
        usr = cls.deserialize(metadata)
        db.session.add(usr)
        db.session.commit()
        return usr

    @classmethod
    def find_or_create(cls, user_info):
        """
        This method populates db when user sign up or login through external auth system
        :param user_info: User data from external auth system
        :param oauth_source: From which oauth source the user coming from e.g. github
        :return: User data from Database
        """
        print(user_info)
        user = models.User.get_by_name(user_info['login'])
        if user:
            return user

        # convert github info to our local user info
        ourinfo = {
            'name': user_info['login'],
            'full_name': user_info.get('name'),
            'email': user_info.get('email')
        }
        user = models.User(**ourinfo)
        # create publisher for this user
        publisher = models.Publisher(name=user.name)
        association = models.PublisherUser(role=models.UserRoleEnum.owner, publisher=publisher, user=user)
        # user.publishers.append(association)
        db.session.add(user)
        db.session.commit()
        return user


def get_authorized_user_info():
    '''
    Return user info (with guaranteed Email) if authorized
    '''
    github = app.config['github']
    resp = github.authorized_response()
    if resp is None or resp.get('access_token') is None:
        raise InvalidUsage('Access Denied', 400)

    session['github_token'] = (resp['access_token'], '')

    user_info = github.get('user').data
    emails = github.get('user/emails').data
    user_info['emails'] = emails

    user_info_schema = UserInfoSchema()
    user_info = user_info_schema.load(user_info).data

    return user_info


def get_jwt_token():
    data = request.get_json()
    user_name = data.get('username', None)
    email = data.get('email', None)
    secret = data.get('secret', None)
    verify = False
    user_id = None
    if user_name is None and email is None:
        raise InvalidUsage('User name or email both can not be empty', 400)

    if secret is None:
        raise InvalidUsage('Secret can not be empty', 400)
    elif user_name is not None:
        try:
            user = models.User.query.filter_by(name=user_name).one()
        except NoResultFound as e:
            app.logger.error(e)
            raise InvalidUsage('user does not exists', 404)
        if secret == user.secret:
            verify = True
            user_id = user.id
    elif email is not None:
        try:
            user = models.User.query.filter_by(email=email).one()
        except NoResultFound as e:
            app.logger.error(e)
            raise InvalidUsage('user does not exists', 404)
        if secret == user.secret:
            verify = True
            user_id = user.id
    if verify:
        return JWT(app.config['JWT_SEED'], user_id).encode()
    else:
        raise InvalidUsage('Secret key do not match', 403)


def generate_signed_url():
    user_id = None
    jwt_status, user_info = get_user_from_jwt(request, app.config['JWT_SEED'])
    if jwt_status:
        user_id = user_info['user']

    data = request.get_json()
    metadata, filedata = data['metadata'], data['filedata']
    publisher, package_name = metadata['owner'], metadata['name']
    res_payload = {'filedata': {}}

    if Package.exists(publisher, package_name):
        status = check_is_authorized('Package::Update', publisher, package_name, user_id)
    else:
        status = check_is_authorized('Package::Create', publisher, package_name, user_id)

    if not status:
        raise InvalidUsage('Not authorized to upload data', 400)

    for relative_path in filedata.keys():
        response = FileData(package_name=package_name,
                            publisher=publisher,
                            relative_path=relative_path,
                            props=filedata[relative_path])
        res_payload['filedata'][relative_path] = response.build_file_information()
    return res_payload


#### helpers

def validate_for_template(descriptor):
    '''
    Validates field types in the descriptor for template, e.g. licenses property should be a list.
    '''
    licenses = descriptor.get('licenses')

    if licenses is None or type(licenses) is list:
        return descriptor

    if type(licenses) is dict:
        license = descriptor.pop('licenses')
        license = license.get('type')
        descriptor['license'] = license
        return descriptor

    descriptor.pop('licenses')

    return descriptor
