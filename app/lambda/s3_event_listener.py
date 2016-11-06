import boto3


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
    pass
