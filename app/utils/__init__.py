import os
from flask import jsonify


def get_zappa_prefix():
    env = os.getenv('STAGE', '')
    if env is not '':
        return '/%s' % (env, )
    return env


def get_s3_cdn_prefix():
    env = os.getenv('STAGE', '')
    if env is not '':
        s3_bucket_name = os.getenv('FLASKS3_BUCKET_NAME')
        return 'https://%s.s3.amazonaws.com' % (s3_bucket_name, )
    return env


def handle_error(error_code, error_message, status_code):
    resp = jsonify(dict(error_code=error_code, message=error_message))
    resp.status_code = status_code
    return resp
