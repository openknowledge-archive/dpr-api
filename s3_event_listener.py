import boto3
import os
import psycopg2
from botocore.client import Config


def write_to_rds_on_s3_metadata_put(event, context):
    """
    {
       "Records":[
          {
             "eventVersion":"2.0",
             "eventSource":"aws:s3",
             "awsRegion":"us-east-1",
             "eventTime":The time, in ISO-8601 format, for example, 1970-01-01T00:00:00.000Z, when S3 finished processing the request,
             "eventName":"event-type",
             "userIdentity":{
                "principalId":"Amazon-customer-ID-of-the-user-who-caused-the-event"
             },
             "requestParameters":{
                "sourceIPAddress":"ip-address-where-request-came-from"
             },
             "responseElements":{
                "x-amz-request-id":"Amazon S3 generated request ID",
                "x-amz-id-2":"Amazon S3 host that processed the request"
             },
             "s3":{
                "s3SchemaVersion":"1.0",
                "configurationId":"ID found in the bucket notification configuration",
                "bucket":{
                   "name":"bucket-name",
                   "ownerIdentity":{
                      "principalId":"Amazon-customer-ID-of-the-bucket-owner"
                   },
                   "arn":"bucket-ARN"
                },
                "object":{
                   "key":"object-key",
                   "size":object-size,
                   "eTag":"object eTag",
                   "versionId":"object version if bucket is versioning-enabled, otherwise null",
                   "sequencer": "a string representation of a hexadecimal value used to determine event sequence,
                       only used with PUTs and DELETEs"
                }
             }
          },
          {
              // Additional events
          }
       ]
    }

    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']
    """
    print '-------------------------------------------------------------'
    print '-------------------------------------------------------------'
    print '-------------------------------------------------------------'
    print '------------------GOT THE MESSAGE----------------------------'
    print '-------------------------------------------------------------'
    print '-------------------------------------------------------------'
    print '-------------------------------------------------------------'

    DSN = os.environ.get("SQLALCHEMY_DATABASE_URI")
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    AWS_REGION = os.environ.get('AWS_REGION')
    s3 = boto3.client('s3',
                      region_name=AWS_REGION,
                      aws_access_key_id=AWS_ACCESS_KEY_ID,
                      aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                      config=Config(signature_version='s3v4'))

    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']
    values = key.split('/')
    publisher, package, version = values[1], values[2], values[4]

    descriptor = s3.get_object(Bucket=bucket, Key=key).response['Body'].read()

    connect = psycopg2.connect(dsn=DSN)
    cursor = connect.cursor()
    cursor.execute("""
                INSERT INTO packages (name, publisher, "descriptor") VALUES (%s, %s, %s,);
                """, (publisher, package, descriptor))
    connect.commit()
    cursor.close()
    connect.close()

