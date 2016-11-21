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


def get_user_info_with_code(code, redirect_uri):
    json_header = {'content-type': 'application/json'}

    token_url = "https://{domain}/oauth/token".\
                format(domain=app.config["AUTH0_DOMAIN"])
    token_payload = {
        'client_id': app.config['AUTH0_CLIENT_ID'],
        'client_secret': app.config['AUTH0_CLIENT_SECRET'],
        'redirect_uri': redirect_uri,
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


def search_user(field, value):
    headers = {'Authorization': "Bearer {token}".
               format(token=get_auth0_token(None)),
               'content-type': "application/json"}
    url = "{AUDIENCE}users?include_fields=true&q={FIELD}:{VALUE}".\
          format(AUDIENCE=app.config["AUTH0_API_AUDIENCE"],
                 FIELD=field, VALUE=value)
    response = requests.get(url=url, headers=headers)
    if response.ok:
        return response.json()
    else:
        return None


def delete_user(user_id):
    headers = {'Authorization': "Bearer {token}".
               format(token=get_auth0_token(None)),
               'content-type': "application/json"}
    url = "{AUDIENCE}users/{USER_ID}".\
        format(AUDIENCE=app.config["AUTH0_API_AUDIENCE"],
               USER_ID=user_id)
    requests.delete(url=url, headers=headers)


def create_user(email, full_name, user_name, password):

    payload = dict(user_metadata=dict(full_name=full_name),
                   connection=app.config['AUTH0_DB_NAME'],
                   email=email,
                   username=user_name,
                   password=password)
    headers = {'Authorization': "Bearer {token}". \
               format(token=get_auth0_token(None)),
               'content-type': "application/json"}
    url = "{AUDIENCE}users".format(AUDIENCE=app.config["AUTH0_API_AUDIENCE"])
    response = requests.post(url=url, data=json.dumps(payload),
                             headers=headers)
    if response.ok:
        return response.json()
    else:
        return None


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
        'grant_type': 'client_credentials',
        'audience': app.config['AUTH0_API_AUDIENCE']
    }
    token_info = requests.post(token_url,
                               data=json.dumps(token_payload),
                               headers=json_header).json()
    return token_info['access_token']
