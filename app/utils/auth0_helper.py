import json
import requests
from flask import current_app as app


def get_user_info(code):
    json_header = {'content-type': 'application/json'}

    token_url = "https://{domain}/oauth/token".format(domain=app.config["AUTH0_DOMAIN"])
    token_payload = {
        'client_id': app.config['AUTH0_CLIENT_ID'],
        'client_secret': app.config['AUTH0_CLIENT_SECRET'],
        'redirect_uri': app.config['AUTH0_CALLBACK_URL'],
        'code': code,
        'grant_type': 'authorization_code'
    }

    token_info = requests.post(token_url, data=json.dumps(token_payload), headers=json_header).json()
    user_url = "https://{domain}/userinfo?access_token={access_token}" \
        .format(domain=app.config["AUTH0_DOMAIN"], access_token=token_info['access_token'])

    user_info = requests.get(user_url).json()
    return user_info
