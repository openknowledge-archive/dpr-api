# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import json

from BeautifulSoup import BeautifulSoup
from flask import request, session
from flask import current_app as app
from sqlalchemy.orm.exc import NoResultFound

from app.auth.annotations import check_is_authorized, get_user_from_jwt
from app.auth.models import JWT, FileData
from app.package.models import BitStore, Package, PackageStateEnum
from app.profile.models import Publisher, User
from app.logic.search import DataPackageQuery
from app.utils import InvalidUsage
from app.utils.helpers import text_to_markdown, dp_in_readme
import app.schemas as schema

# TODO: authz
def get_package(publisher, package):
    '''
    Returns info for package - modified descriptor, bitstore URL for descriptor,
    views and short README
    '''
    metadata = get_metadata_for_package(publisher, package)
    if not metadata:
        return None

    descriptor = metadata.get('descriptor')
    readme = metadata.get('readme')
    descriptor['owner'] = publisher
    readme_variables_replaced = dp_in_readme(readme, descriptor)
    descriptor["readme"] = text_to_markdown(readme_variables_replaced)

    dataViews = descriptor.get('views') or []

    bitstore = BitStore(publisher, package)
    datapackage_json_url_in_s3 = bitstore.build_s3_object_url('datapackage.json')
    readme_short_markdown = text_to_markdown(metadata.get('readme', ''))
    readme_short = ''.join(BeautifulSoup(readme_short_markdown).findAll(text=True)) \
        .split('\n\n')[0].replace(' \n', '') \
        .replace('\n', ' ').replace('/^ /', '')

    datapackage = dict(
        descriptor=descriptor,
        datapackag_url=datapackage_json_url_in_s3,
        views=dataViews,
        short_readme=readme_short
    )

    return datapackage

def get_metadata_for_package(publisher, package):
    '''
    Returns metadata for given package owned by publisher
    '''
    data = Package.query.join(Publisher).\
        filter(Publisher.name == publisher,
               Package.name == package,
               Package.status == PackageStateEnum.active).\
        first()
    if not data:
        return None

    metadata_schema = schema.PackageMetadataSchema()
    metadata = metadata_schema.dump(data).data

    return metadata


def finalize_package_publish(user_id, datapackage_url):
    '''
    Gets the datapackage.json and README from S3 and imports into database.
    Returns status "queued" if ok, else - None
    '''
    publisher, package, version = BitStore.extract_information_from_s3_url(datapackage_url)
    if Package.is_package_exists(publisher, package):
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


def get_package_names_for_publisher(publisher):
    metadata = Package.query.join(Publisher).\
        with_entities(Package.name).\
        filter(Publisher.name == publisher).all()
    if len(metadata) is 0:
        raise InvalidUsage('No Data Package Found For The Publisher', 404)
    keys = []
    for d in metadata:
        keys.append(d[0])
    return keys

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

    user_info_schema = schema.UserInfoSchema()
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
            user = User.query.filter_by(name=user_name).one()
        except NoResultFound as e:
            app.logger.error(e)
            raise InvalidUsage('user does not exists', 404)
        if secret == user.secret:
            verify = True
            user_id = user.id
    elif email is not None:
        try:
            user = User.query.filter_by(email=email).one()
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

    if Package.is_package_exists(publisher, package_name):
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
