import boto3
import os
from flask_sqlalchemy import SQLAlchemy

# Instantiate and start DB
db = SQLAlchemy()

# Need to pass default blank value to access id and access key for testing
aws_access_key_id = os.environ.get('aws_access_key_id', '')
aws_secret_access_key = os.environ.get('aws_secret_access_key', '')
# Need to give some default real region as blank value throws error
region = os.environ.get('aws_region', 'eu-west-1')

s3 = boto3.resource('s3',
                    region_name=region,
                    aws_access_key_id=aws_access_key_id,
                    aws_secret_access_key=aws_secret_access_key)
