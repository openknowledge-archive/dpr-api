from functools import wraps
from flask import request, jsonify, _request_ctx_stack
from flask import current_app as app

from app.utils.jwt_utilities import JWTHelper


def handle_error(error, status_code):
    resp = jsonify(error)
    resp.status_code = status_code
    return resp


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        jwt_helper = JWTHelper(app.config['API_KEY'])

        auth = request.headers.get('Authorization', None)

        if not auth:
            return handle_error({'error_code': 'authorization_header_missing',
                                 'description': 'Authorization header is expected'}, 401)
        parts = auth.split()
        if parts[0].lower() != 'bearer':
            return handle_error(
                {'error_code': 'invalid_header', 'description': 'Authorization header must start with Bearer'}, 401)
        elif len(parts) == 1:
            return handle_error({'error_code': 'invalid_header', 'description': 'Token not found'}, 401)
        elif len(parts) > 2:
            return handle_error(
                {'error_code': 'invalid_header', 'description': 'Authorization header must be Bearer + \s + token'}, 401)
        token = parts[1]
        try:
            payload = jwt_helper.decode(token)
        except Exception as e:
            return handle_error({'code': 'jwt_error', 'description': e.message}, 400)
        _request_ctx_stack.top.current_user = user = payload
        return f(*args, **kwargs)

    return decorated
