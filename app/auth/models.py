# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime
import jwt
from app.package.models import BitStore
from app.utils import InvalidUsage

class JWT(object):

    def __init__(self, api_key, user_id=None,
                 expiration_hour=24):
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
            raise InvalidUsage("Token is expired")
        except jwt.DecodeError:
            raise InvalidUsage('Token signature is invalid')
        except Exception:
            raise Exception('Unable to parse authentication token.')

    def get_decoded_user_id(self, token):
        return self.decode(token)['user']


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
        if 'acl' in self.props:
            kwargs['acl'] = self.props['acl']
        post = self.bitstore.\
            generate_pre_signed_post_object(self.relative_path,
                                            md5=self.props['md5'],
                                            **kwargs)
        return post

    def build_file_information(self):
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
