import boto3
import os
from os.path import join, dirname
from dotenv import load_dotenv
from botocore.client import Config
from flask_sqlalchemy import SQLAlchemy

dot_env_path = join(dirname(__file__), '../.env')
load_dotenv(dot_env_path)

# Instantiate and start DB
db = SQLAlchemy()

# Need to pass default blank value to access id and access key for testing
aws_access_key_id = os.environ.get('AWS_ACCESS_KEY_ID', '')
aws_secret_access_key = os.environ.get('AWS_SECRET_ACCESS_KEY', '')
# Need to give some default real region as blank value throws error
region = os.environ.get('AWS_REGION', 'eu-west-1')

s3 = boto3.client('s3',
                  region_name=region,
                  aws_access_key_id=aws_access_key_id,
                  aws_secret_access_key=aws_secret_access_key,
                  config=Config(signature_version='s3v4'))
