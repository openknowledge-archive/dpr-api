import os
import json
import logging
import boto3
from flask import Flask, jsonify, request
from flask.views import MethodView
from flasgger import Swagger

dpr_api = Flask(__name__)
logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

dpr_api.config['SWAGGER'] = {
    "swagger_version": "2.0",
    "title": "DPR API",
    "specs": [
            {
                "version": "0.0.1",
                "title": "v1",
                "endpoint": 'spec',
                "description": "First Cut for DPR API",
                "route": '/v1/spec',
                "rule_filter": lambda rule: rule.endpoint.startswith('api_v1')
            }
        ]
}

Swagger(dpr_api)
s3 = boto3.resource('s3')


class MetaDataApi(MethodView):

    def get(self, publisher, package=None):
        """
        DPR meta-data get operation.
        This API is responsible for getting datapackage.json from S3.
        If only package name is not in path then it returns back all data package names.
        If package and publisher is in path then it returns the content of the data package metadata.
        ---
        tags:
            - metadata
        parameters:
            - in: path
              name: publisher
              type: string
              required: true
              description: publisher name
            - in: path
              name: package
              type: string
              required: false
              description: package name, use this to retrieve the data package metadata contents
        responses:
            201:
                description: Get All Keys
                schema:
                    id: get_all_keys
                    properties:
                        data:
                            type: array
                            items:
                                type: string
                            description: All data package names for the publisher
            202:
                description: Get Data package for one key
                schema:
                    id: get_data_package
                    properties:
                        data:
                            type: map
                            description: The datapackage.json
            501:
                description: Error Message
                schema:
                    id: get_package_error
                    properties:
                        status:
                            type: string
                            description: Status of the operation
                        message:
                            type: string
                            description: Exception message
        """
        bucket_name = os.environ.get('METADATA_BUCKET', 'test')
        bucket = s3.Bucket(bucket_name)
        if package is None:
            keys = []
            prefix = "{prefix}/{publisher}/".format(prefix=os.environ.get('METADATA_KEY_PREFIX', 'dpr_metadata'),
                                                    publisher=publisher)
            try:
                for ob in bucket.objects.filter(Prefix=prefix):
                    keys.append(ob.key.replace(prefix, ''))
                return jsonify({'data': keys}), 201
            except Exception as e:
                return jsonify({'status': 'ko', 'message': e.message}), 501
        else:
            key = "{prefix}/{publisher}/{package}.json"\
                .format(prefix=os.environ.get('METADATA_KEY_PREFIX', 'dpr_metadata'),
                        publisher=publisher, package=package)
            try:
                response = s3.Object(Bucket=bucket_name, Key=key).get()
                return jsonify({"data": json.loads(response['Body'].read())}), 202
            except Exception as e:
                return jsonify({'status': 'ko', 'message': e.message}), 501

    def put(self, publisher, package):
        """
        DPR meta-data put operation.
        This API is responsible for pushing  datapackage.json to S3.
        ---
        tags:
            - metadata
        parameters:
            - in: path
              name: publisher
              type: string
              required: true
              description: publisher name
            - in: path
              name: package
              type: string
              required: true
              description: package name
        responses:
            501:
                description: Error Message
                schema:
                    id: put_package_error
                    properties:
                        status:
                            type: string
                            description: Status of the operation
                        message:
                            type: string
                            description: Exception message
            200:
                description: Success Message
                schema:
                    id: put_package_success
                    properties:
                        status:
                            type: string
                            description: Status of the operation
        """
        key = "{prefix}/{publisher}/{package}.json"\
            .format(prefix=os.environ.get('METADATA_KEY_PREFIX', 'dpr_metadata'),
                    publisher=publisher, package=package)
        bucket = os.environ.get('METADATA_BUCKET', 'test')
        logger.info("Putting data in {b} and key {k}".format(b=bucket, k=key))
        logger.info(request.data)
        try:
            s3.Bucket(bucket).put_object(Key=key, Body=request.data)
            return jsonify({'status': 'ok'}), 200
        except Exception as e:
            return jsonify({'status': 'ko', 'message': e.message}), 501


view = MetaDataApi.as_view('metadata')
dpr_api.add_url_rule('/api/v1/metadata/<publisher>/<package>',
                     view_func=view,
                     methods=["GET", "PUT"],
                     endpoint="api_v1")


if __name__ == '__main__':
    dpr_api.run(debug=True)
