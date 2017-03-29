# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import os
from flask import jsonify


def handle_error(error_code, error_message, status_code):
    resp = jsonify(dict(error_code=error_code, message=error_message))
    resp.status_code = status_code
    return resp
