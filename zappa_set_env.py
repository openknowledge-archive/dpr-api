# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import json
import os
from os.path import join, dirname, expanduser
import sys
from dotenv import load_dotenv

env_variables = [
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_REGION",

    "AUTH0_CLIENT_ID",
    "AUTH0_CLIENT_SECRET",
    "AUTH0_DOMAIN",
    "AUTH0_DB_NAME",
    "AUTH0_CALLBACK_URL",
    "AUTH0_API_AUDIENCE",

    "S3_BUCKET_NAME",
    'FLASKS3_BUCKET_NAME',

    "SQLALCHEMY_DATABASE_URI",
]


def write_aws_credential():
    key = "aws_access_key_id={k}\n".format(k=os.getenv('AWS_ACCESS_KEY_ID'))
    secret = "aws_secret_access_key={k}\n".format(
        k=os.getenv('AWS_SECRET_ACCESS_KEY'))
    region = "region={k}\n".format(k=os.getenv('AWS_REGION'))
    file_content = ['[default]\n', key, secret,
                    '[profile default]\n', 'output=json\n', region]
    home = expanduser("~")
    with open(home + '/.aws/credentials', 'w') as f:
        f.writelines(file_content)


def write_env_for_event():
    current_dir = os.path.abspath('.')
    variables = []
    for ev in env_variables:
        variables.append("{var}={value}\n".format(var=ev, value=os.getenv(ev)))
    with open(current_dir + '/.cred', 'w') as f:
        f.writelines(variables)


if __name__ == "__main__":

    environment = None
    if len(sys.argv) == 1:
        environment = 'stage'
    else:
        environment = sys.argv[1]

    current_dir = os.path.abspath('.')
    # For dev
    try:
        dot_env_path = join(dirname(__file__), './.env')
        load_dotenv(dot_env_path)
    except Exception as e:
        print (e.message)

    with open(current_dir + '/zappa_settings.json', 'r') as f:
        json_data = json.load(f)
        env = json_data[environment]['environment_variables']

        for env_variable in env_variables:
            env[env_variable] = os.getenv(env_variable)
        json_data[environment]['environment_variables'] = env
        with open(current_dir + '/zappa_settings_deploy.json', 'w') as f:
            f.write(json.dumps(json_data, indent=4,))
    write_aws_credential()
    write_env_for_event()

