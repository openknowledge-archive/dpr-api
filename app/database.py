import boto3
import os
from flask_sqlalchemy import SQLAlchemy

# Instantiate and start DB
db = SQLAlchemy()
s3 = boto3.resource('s3')

aws_access_key_id = os.environ.get('aws_access_key_id', None)
aws_secret_access_key = os.environ.get('aws_secret_access_key', None)
region = os.environ.get('region_name', None)

if aws_secret_access_key is None or aws_access_key_id is None:
    s3 = boto3.resource('s3',
                        region_name=region,
                        aws_access_key_id=aws_access_key_id,
                        aws_secret_access_key=aws_secret_access_key)
