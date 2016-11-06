import boto3
import os
from botocore.client import Config
from flask_sqlalchemy import SQLAlchemy

# Instantiate and start DB
db = SQLAlchemy()

s3 = boto3.client('s3',
                  #region_name=app.config['AWS_REGION'], #os.environ.get('AWS_REGION', 'eu-west-1'),
                  #aws_access_key_id=app.config['AWS_ACCESS_KEY_ID'], #os.environ.get('AWS_ACCESS_KEY_ID', ''),
                  #aws_secret_access_key=app.config['AWS_SECRET_ACCESS_KEY'], #os.environ.get('AWS_SECRET_ACCESS_KEY', ''),
                  config=Config(signature_version='s3v4'))
