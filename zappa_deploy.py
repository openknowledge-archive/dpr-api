# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import json
import os
import sys
from subprocess import check_output, CalledProcessError
from os.path import join, dirname, expanduser
from dotenv import load_dotenv

env_variables = [
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_REGION",

    "AUTH0_CLIENT_ID",
    "AUTH0_CLIENT_SECRET",
    "AUTH0_DOMAIN",
    "AUTH0_DB_NAME",
    "AUTH0_API_AUDIENCE",

    "S3_BUCKET_NAME",
    'FLASKS3_BUCKET_NAME',

    "SQLALCHEMY_DATABASE_URI",
]
zappa_final_conf_file = "zappa_settings_deploy.json"
zappa_conf_file = "zappa_settings.json"


def write_aws_credential():
    file_content = list()
    file_content.append('[default]\n')
    file_content.append("aws_access_key_id={k}\n"
                        .format(k=os.getenv('AWS_ACCESS_KEY_ID')))
    file_content.append("aws_secret_access_key={k}\n"
                        .format(k=os.getenv('AWS_SECRET_ACCESS_KEY')))
    file_content.append('[profile default]\n')
    file_content.append('output=json\n')
    file_content.append("region={k}\n".format(k=os.getenv('AWS_REGION')))
    home = expanduser("~")

    if not os.path.exists(home + '/.aws'):
        os.makedirs(home + '/.aws')

    with open(home + '/.aws/credentials', 'w') as fac:
        fac.writelines(file_content)


def create_zappa_settings(stage_name):
    current_dir = os.path.abspath('.')
    # For dev
    try:
        dot_env_path = join(dirname(__file__), './.env')
        load_dotenv(dot_env_path)
    except Exception as e:
        print(e.message)

    with open(current_dir + '/' + zappa_conf_file, 'r') as fr:
        json_data = json.load(fr)
        env = json_data[stage_name]['environment_variables']

        for env_variable in env_variables:
            env[env_variable] = os.getenv(env_variable)
        json_data[stage_name]['environment_variables'] = env
        with open(current_dir + '/' + zappa_final_conf_file, 'w') as fw:
            fw.write(json.dumps(json_data, indent=4,))


def run_zappa(stage_name):
    current_dir = os.path.abspath('.')
    code = 0
    try:
        check_output(['zappa', 'deploy', stage_name,
                      '-s', current_dir + '/' + zappa_final_conf_file])
    except CalledProcessError as e:
        code = e.returncode
        print (e)

    if code is not 0:
        try:
            print('This application already deployed calling for update')
            check_output(['zappa', 'update', stage_name,
                          '-s', current_dir + '/' + zappa_final_conf_file])
        except CalledProcessError as e:
            print(e)

if __name__ == '__main__':
    env = None
    if len(sys.argv) == 1:
        env = 'stage'
    else:
        env = sys.argv[1]
    create_zappa_settings(stage_name=env)
    write_aws_credential()
    run_zappa(env)
    check_output(['python', 'manager.py', 'dropdb'])
    check_output(['python', 'manager.py', 'createdb'])
    check_output(['python', 'manager.py', 'populate'])

