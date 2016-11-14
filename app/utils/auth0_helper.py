# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import json
import time
import requests
from flask import current_app as app
import jwt

token = None


def get_user_info_with_code(code):
    json_header = {'content-type': 'application/json'}

    token_url = "https://{domain}/oauth/token".\
                format(domain=app.config["AUTH0_DOMAIN"])
    token_payload = {
        'client_id': app.config['AUTH0_CLIENT_ID'],
        'client_secret': app.config['AUTH0_CLIENT_SECRET'],
        'redirect_uri': app.config['AUTH0_CALLBACK_URL'],
        'code': code,
        'grant_type': 'authorization_code'
    }

    token_info = requests.post(token_url,
                               data=json.dumps(token_payload),
                               headers=json_header).json()
    user_url = "https://{domain}/userinfo?access_token={access_token}" \
        .format(domain=app.config["AUTH0_DOMAIN"],
                access_token=token_info['access_token'])

    response = requests.get(user_url)
    if response.ok:
        return response.json()
    else:
        return None


def get_user(user_id):
    headers = {'Authorization': "Bearer {token}".\
               format(token=get_auth0_token(None)),
               'content-type': "application/json"}
    url = "{AUDIENCE}users/{user_id}".\
          format(AUDIENCE=app.config["AUTH0_API_AUDIENCE"],
                 user_id=user_id)
    response = requests.request("GET", url, headers=headers)
    return response.json()


def update_user_secret(user_id):
    headers = {'Authorization': "Bearer {token}".\
               format(token=get_auth0_token(None)),
               'content-type': "application/json"}
    url = "{AUDIENCE}users/{user_id}".\
          format(AUDIENCE=app.config["AUTH0_API_AUDIENCE"],
                 user_id=user_id)

    payload = {"user_metadata": {"secret": "supersecret"}}
    response = requests.request("PATCH", url,
                                data=json.dumps(payload),
                                headers=headers)
    return response.json()


def update_user_secret_from_user_info(user_info):
    user_id = user_info['user_id']
    if 'user_metadata' in user_info and \
    'secret' not in user_info['user_metadata']:
        update_user_secret(user_id)
    else:
        update_user_secret(user_id)


def get_auth0_token(jwt_token):
    if jwt_token is not None:
        token_payload = jwt.decode(jwt_token, verify=False)
        if int(time.time()) > int(token_payload['exp']):
            return jwt_token

    json_header = {'content-type': 'application/json'}

    token_url = "https://{domain}/oauth/token".\
                format(domain=app.config["AUTH0_DOMAIN"])

    token_payload = {
        'client_id': app.config['AUTH0_CLIENT_ID'],
        'client_secret': app.config['AUTH0_CLIENT_SECRET'],
        'redirect_uri': app.config['AUTH0_CALLBACK_URL'],
        'grant_type': 'client_credentials',
        'audience': app.config['AUTH0_API_AUDIENCE']
    }
    token_info = requests.post(token_url,
                               data=json.dumps(token_payload),
                               headers=json_header).json()
    return token_info['access_token']
