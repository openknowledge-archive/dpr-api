import boto3
import json
import logging
import psycopg2

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.info("Starting What's Up Handler...")


def get_env():
    env_var = dict()
    with open('.cred') as f:
        for line in f:
            vals = line.replace('\n', '').split("=")
            env_var[vals[0]] = vals[1]
    return env_var


def write_to_rds_on_s3_metadata_put(event, context):
    """
    {u'Records':
        [
            {
                u'eventVersion': u'2.0',
                u'eventTime': u'2016-11-08T05:05:40.665Z',
                u'requestParameters':
                    {
                        u'sourceIPAddress': u'125.18.97.185'
                    },
                u's3': {
                    u'configurationId': u'arn:aws:lambda:us-west-2:679343311282:function:dpr-api-stage',
                    u'object': {
                        u'eTag': u'536f64155a6bde60e5ef304e5c6aa8f3',
                        u'sequencer': u'0058215D24A159AD48',
                        u'key': u'metadata/publisher/metadata.json',
                        u'size': 25
                    },
                    u'bucket':
                        {
                            u'arn': u'arn:aws:s3:::neo20iitkgp',
                            u'name': u'neo20iitkgp',
                            u'ownerIdentity':
                                {
                                    u'principalId': u'A3EX8T81R8JZ81'
                                }
                            },
                            u's3SchemaVersion': u'1.0'
                        },
                    u'responseElements':
                        {
                            u'x-amz-id-2': u'4qPPxycXBM8Kx4SOzvhbOkAKqXpXBAy47U3sUtj9PzrCW4qTWiDFXdZmXBlmsp02',
                            u'x-amz-request-id': u'9800FAFB4182CD48'
                        },
                    u'awsRegion': u'us-west-2',
                    u'eventName': u'ObjectCreated:Put',
                    u'userIdentity': {
                        u'principalId': u'A3EX8T81R8JZ81'
                    },
                    u'eventSource': u'aws:s3'
                }
            ]
        }
    """

    environment_variables = get_env()

    print environment_variables

    DSN = environment_variables.get("SQLALCHEMY_DATABASE_URI")
    AWS_ACCESS_KEY_ID = environment_variables.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = environment_variables.get('AWS_SECRET_ACCESS_KEY')
    AWS_REGION = environment_variables.get('AWS_REGION')

    s3 = boto3.client('s3',
                      region_name=AWS_REGION,
                      aws_access_key_id=AWS_ACCESS_KEY_ID,
                      aws_secret_access_key=AWS_SECRET_ACCESS_KEY)

    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']
    values = key.split('/')
    publisher, package, version = values[1], values[2], values[4]

    response = s3.get_object(Bucket=bucket, Key=key)
    descriptor = json.dumps(response['Body'].read())

    connect = psycopg2.connect(dsn=DSN)
    cursor = connect.cursor()

    cursor.execute("""
                INSERT INTO packages (publisher, name, "descriptor") VALUES (%s, %s, %s)
                ON CONFLICT (name, publisher) DO UPDATE SET "descriptor" = %s
                """, (publisher, package, descriptor, descriptor))
    connect.commit()
    cursor.close()
    connect.close()

