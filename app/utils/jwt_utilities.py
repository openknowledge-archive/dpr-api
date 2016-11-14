# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import base64
import datetime
import jwt


class JWTHelper(object):

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
            "exp": datetime.datetime.utcnow()+
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
