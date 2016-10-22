import os
from functools import wraps
from flask import Blueprint
from flask import redirect
from flask import request, jsonify, _request_ctx_stack
from flask import current_app as app
from app.mod_api.models import User

from app.utils.auth0_helper import get_user_info
from app.utils.jwt_utilities import JWTHelper

mod_auth = Blueprint('auth', __name__,  url_prefix='/auth')


def handle_error(error, status_code):
    resp = jsonify(error)
    resp.status_code = status_code
    return resp


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'Client' in request.headers:
            if request.headers['Client'] == 'CLI':
                data = request.get_json()
                user_id = data.get('user_id', None)
                user_secret = data.get('user_secret', None)
                if user_id is None or user_secret is None:
                    return handle_error(
                        {'code': 'no_user_id_or_user_secret', 'description': 'User id and secret does not exists'}, 401)
                user = User.query.filter_by(user_id=user_id).first()
                if user is None:
                    return handle_error(
                        {'code': 'invalid_user_id', 'description': 'User user id does not exists'}, 401)
                if user.secret_key != user_secret:
                    return handle_error(
                        {'code': 'invalid_secret', 'description': 'User secret and user id does not match'}, 401)

            elif request.headers['Client'] == 'WEB':
                jwt_helper = JWTHelper(app.config['API_KEY'])

                auth = request.headers.get('Authorization', None)

                if not auth:
                    return handle_error({'code': 'authorization_header_missing',
                                         'description': 'Authorization header is expected'}, 401)
                parts = auth.split()
                if parts[0].lower() != 'bearer':
                    return handle_error(
                        {'code': 'invalid_header', 'description': 'Authorization header must start with Bearer'}, 401)
                elif len(parts) == 1:
                    return handle_error({'code': 'invalid_header', 'description': 'Token not found'}, 401)
                elif len(parts) > 2:
                    return handle_error(
                        {'code': 'invalid_header', 'description': 'Authorization header must be Bearer + \s + token'}, 401)
                token = parts[1]
                try:
                    payload = jwt_helper.decode(token)
                    print payload
                except Exception as e:
                    return handle_error({'code': 'jwt_error', 'description': e.message}, 400)
                _request_ctx_stack.top.current_user = user = payload
        else:
            return handle_error(
                {'code': 'invalid_header', 'description': 'Value Client must be header'}, 401)
        return f(*args, **kwargs)

    return decorated


@mod_auth.route("/callback")
def callback_handling():
    code = request.args.get('code')
    user_info = get_user_info(code)
    user_id = user_info['user_id']


    # TODO SYNC with local DB

    jwt_helper = JWTHelper(app.config['API_KEY'], user_id)
    return jsonify({'jwt': jwt_helper.encode(), 'user': user_info})


@mod_auth.route('/get_jwt', methods=['POST'])
@requires_auth
def get_jwt():
    data = request.data
    user_id = data['user_id']
    # TODO get user id from db

    user_secret = data['user_secret']

    jwt_helper = JWTHelper(app.config['API_KEY'], user_id)
    return jwt_helper.encode()

@mod_auth.route("/ll")
def ll():
    return redirect('https://subhankarb.auth0.com/login?client=4dNuUsLVWWsLmdO0WMP04g2bDNrlS9fb')
