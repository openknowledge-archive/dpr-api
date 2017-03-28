# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import os
from flask import jsonify


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
