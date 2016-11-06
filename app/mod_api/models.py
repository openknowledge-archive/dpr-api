import json
from sqlalchemy import UniqueConstraint

from app.database import s3, db
from sqlalchemy.dialects.postgresql import JSON
from flask import current_app as app


class MetaDataS3(object):
    prefix = 'metadata'

    def __init__(self, publisher, package='', version='latest', body=None):
        self.publisher = publisher
        self.package = package
        self.version = version
        self.body = body

    def validate(self):
        data = json.loads(self.body)
        if 'name' not in data:
            return False
        if data['name'] == '':
            return False
        return True

    def save(self):
        bucket_name = app.config['S3_BUCKET_NAME']
        key = self.build_s3_key('datapackage.json')
        s3.aws_secret_access_key = app.config['AWS_SECRET_ACCESS_KEY']
        s3.aws_access_key_id = app.config['AWS_ACCESS_KEY_ID']
        s3.region_name = app.config['AWS_REGION']
        s3.put_object(Bucket=bucket_name, Key=key, Body=self.body)

    def get_metadata_body(self):
        bucket_name = app.config['S3_BUCKET_NAME']
        key = self.build_s3_key('datapackage.json')
        s3.aws_secret_access_key = app.config['AWS_SECRET_ACCESS_KEY']
        s3.aws_access_key_id = app.config['AWS_ACCESS_KEY_ID']
        s3.region_name = app.config['AWS_REGION']
        response = s3.get_object(Bucket=bucket_name, Key=key)
        return response['Body'].read()

    def get_all_metadata_name_for_publisher(self):
        bucket_name = app.config['S3_BUCKET_NAME']
        keys = []
        prefix = self.build_s3_prefix()
        s3.aws_secret_access_key = app.config['AWS_SECRET_ACCESS_KEY']
        s3.aws_access_key_id = app.config['AWS_ACCESS_KEY_ID']
        s3.region_name = app.config['AWS_REGION']
        list_objects = s3.list_objects(Bucket=bucket_name, Prefix=prefix)
        if list_objects is not None and 'Contents' in list_objects:
            for ob in s3.list_objects(Bucket=bucket_name, Prefix=prefix)['Contents']:
                keys.append(ob['Key'])
        return keys

    def build_s3_key(self, path):
        return "{prefix}/{publisher}/{package}/_v/{version}/{path}"\
            .format(prefix=self.prefix, publisher=self.publisher,
                    package=self.package, version=self.version, path=path)

    def build_s3_prefix(self):
        return "{prefix}/{publisher}".format(prefix=self.prefix, publisher=self.publisher)

    def generate_pre_signed_put_obj_url(self, path):
        bucket_name = app.config['S3_BUCKET_NAME']
        key = self.build_s3_key(path)
        params = {'Bucket': bucket_name, 'Key': key}
        s3.aws_secret_access_key = app.config['AWS_SECRET_ACCESS_KEY']
        s3.aws_access_key_id = app.config['AWS_ACCESS_KEY_ID']
        s3.region_name = app.config['AWS_REGION']
        url = s3.generate_presigned_url('put_object', Params=params, ExpiresIn=3600)
        return url


class User(db.Model):

    __tablename__ = 'user'

    user_id = db.Column(db.String(64), primary_key=True)
    email = db.Column(db.String(128), index=True)
    secret = db.Column(db.String(64))
    user_name = db.Column(db.String(64))

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'user_id': self.user_id,
            'email': self.email,
            'name': self.user_name,
            'secret': self.secret
        }

    @staticmethod
    def create_or_update_user_from_callback(user_info):
        user_id = user_info['user_id']
        user = User.query.filter_by(user_id=user_id).first()
        if user is None:
            user = User()
            user.email = user_info['email']
            user.secret = user_info['user_metadata']['secret']
            user.user_id = user_info['user_id']
            user.user_name = user_info['username']
            db.session.add(user)
            db.session.commit()
        return user


class MetaDataDB(db.Model):
    __tablename__ = "packages"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    publisher = db.Column(db.String(64))
    descriptor = db.Column(JSON)
    status = db.Column(db.String(16))
    private = db.Column(db.Boolean)

    __table_args__ = (
        UniqueConstraint("name", "publisher"),
    )

    def __init__(self, name, publisher):
        self.name = name
        self.publisher = publisher
