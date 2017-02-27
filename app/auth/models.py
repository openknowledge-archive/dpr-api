# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime
import jwt
import json
import time
import requests
from flask import current_app as app
from app.package.models import BitStore


class JWT(object):
    def __init__(self, api_key, user_id=None,
                 expiration_hour=1):
        self.secret = api_key
        self.user_id = user_id
        self.expiration_hour = expiration_hour
        self.issuer = 'dpr-api'
        self.algorithm = 'HS256'

    def encode(self):
        return jwt.encode(self.build_payload(),
                          self.secret,
                          algorithm=self.algorithm)

    def build_payload(self):
        return {
            'iss': self.issuer,
            "user": self.user_id,
            "exp": datetime.datetime.utcnow() +
                   datetime.timedelta(hours=self.expiration_hour),
            "iat": datetime.datetime.utcnow()
        }

    def decode(self, token):
        try:
            return jwt.decode(token,
                              self.secret,
                              algorithm=self.algorithm,
                              issuer=self.issuer)
        except jwt.ExpiredSignature:
            raise Exception("token is expired")
        except jwt.DecodeError:
            raise Exception('token signature is invalid')
        except Exception:
            raise Exception('Unable to parse authentication token.')

    def get_decoded_user_id(self, token):
        return self.decode(token)['user']


class Auth0(object):
    def __init__(self):
        self.client_id = app.config['AUTH0_CLIENT_ID']
        self.client_secret = app.config['AUTH0_CLIENT_SECRET']
        self.auth0_domain = app.config["AUTH0_DOMAIN"]
        self.auth0_audience = "https://{domain}/api/v2/".format(domain=self.auth0_domain)
        self.auth0_api = "https://{domain}/api/v2".format(domain=self.auth0_domain)
        self.jwt_token = self.get_auth0_token()
        self.headers = {'Authorization': "Bearer {token}".format(token=self.jwt_token),
                        'content-type': "application/json"}

    def get_auth0_token(self):
        jwt_token = app.config.get('AUTH0_JWT', None)
        if jwt_token is not None:
            token_payload = jwt.decode(jwt_token, verify=False)
            if int(time.time()) > int(token_payload['exp']):
                return jwt_token

        json_header = {'content-type': 'application/json'}

        token_url = "https://{domain}/oauth/token". \
            format(domain=self.auth0_domain)

        token_payload = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'client_credentials',
            'audience': self.auth0_audience
        }
        token_info = requests.post(token_url,
                                   data=json.dumps(token_payload),
                                   headers=json_header).json()
        return token_info['access_token']

    def get_user_info_with_code(self, code, redirect_uri):
        json_header = {'content-type': 'application/json'}

        token_url = "https://{domain}/oauth/token". \
            format(domain=app.config["AUTH0_DOMAIN"])
        token_payload = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'redirect_uri': redirect_uri,
            'code': code,
            'grant_type': 'authorization_code'
        }

        token_info = requests.post(token_url,
                                   data=json.dumps(token_payload),
                                   headers=json_header).json()
        user_url = "https://{domain}/userinfo?access_token={access_token}" \
            .format(domain=self.auth0_domain,
                    access_token=token_info['access_token'])

        response = requests.get(user_url)
        if response.ok:
            return response.json()
        else:
            return None

    def get_user(self, user_id):
        url = "{AUDIENCE}/users/{user_id}". \
            format(AUDIENCE=self.auth0_api,
                   user_id=user_id)
        response = requests.request("GET", url, headers=self.headers)
        return response.json()

    def search_user(self, field, value):

        url = "{AUDIENCE}/users?include_fields=true&q={FIELD}:{VALUE}". \
            format(AUDIENCE=self.auth0_api,
                   FIELD=field, VALUE=value)
        response = requests.get(url=url, headers=self.headers)
        if response.ok:
            return response.json()
        else:
            return None

    def delete_user(self, user_id):

        url = "{AUDIENCE}/users/{USER_ID}". \
            format(AUDIENCE=self.auth0_api,
                   USER_ID=user_id)
        requests.delete(url=url, headers=self.headers)

    def create_user(self, email, full_name, user_name, password):

        payload = dict(user_metadata=dict(full_name=full_name),
                       connection=app.config['AUTH0_DB_NAME'],
                       email=email,
                       username=user_name,
                       password=password)

        url = "{AUDIENCE}/users".format(AUDIENCE=self.auth0_api)
        response = requests.post(url=url, data=json.dumps(payload),
                                 headers=self.headers)
        if response.ok:
            return response.json()
        else:
            return None


class FileData(object):

    def __init__(self, package_name, publisher,
                 relative_path, props):
        self.package_name = package_name
        self.publisher = publisher
        self.relative_path = relative_path
        self.props = props
        self.bitstore = BitStore(publisher=publisher,
                                 package=package_name)

    def _generate_bitstore_url(self):
        kwargs = {}
        if 'type' in self.props:
            kwargs['file_type'] = self.props['type']
        if 'acl' in self.props:
            kwargs['acl'] = self.props['acl']
        post = self.bitstore.\
            generate_pre_signed_post_object(self.relative_path,
                                            md5=self.props['md5'],
                                            **kwargs)
        return post

    def get_response(self):
        response = {
            'name': self.props['name'],
            'md5': self.props['md5'],
        }
        if 'type' in self.props:
            response['type'] = self.props['type']
        if 'acl' in self.props:
            response['acl'] = self.props['acl']

        post = self._generate_bitstore_url()
        response['upload_url'] = post['url']
        response['upload_query'] = post['fields']
        return response
