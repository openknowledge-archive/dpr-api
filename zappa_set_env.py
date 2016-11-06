import json
import os
import sys
from os.path import join, dirname
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

if __name__ == "__main__":

    stage = None
    if len(sys.argv) == 1:
        stage = 'stage'
    else:
        stage = sys.argv[1]
    current_dir = os.path.abspath('.')
    # For dev
    try:
        dot_env_path = join(dirname(__file__), './.env')
        load_dotenv(dot_env_path)
    except Exception as e:
        print e.message

    with open(current_dir + '/zappa_settings.json', 'r') as f:
        json_data = json.load(f)
        env = json_data[stage]['environment_variables']

        for env_variable in env_variables:
            env[env_variable] = os.getenv(env_variable)
        json_data[stage]['environment_variables'] = env
    with open(current_dir + '/zappa_settings_deploy.json', 'w') as f:
        f.write(json.dumps(json_data, indent=4,))

    key = "aws_access_key_id={k}\n".format(k=os.getenv('AWS_ACCESS_KEY_ID'))
    secret = "aws_secret_access_key={k}\n".format(k=os.getenv('AWS_SECRET_ACCESS_KEY'))
    region = "region={k}\n".format(k=os.getenv('AWS_REGION'))
    file_content = ['[default]\n', key, secret,
                    '[profile default]\n', 'output=json\n', region]

    with open('/root/.aws/credentials', 'w') as f:
        f.writelines(file_content)
