from app.database import s3, db
from flask import current_app as app


class MetaDataS3(object):
    prefix = 'metadata'

    def __init__(self, publisher, package='', version='latest', body=None):
        self.publisher = publisher
        self.package = package
        self.version = version
        self.body = body

    def save(self):
        bucket_name = app.config['S3_BUCKET_NAME']
        key = self.build_s3_key()
        s3.put_object(Bucket=bucket_name, Key=key, Body=self.body)

    def get_metadata_body(self):
        bucket_name = app.config['S3_BUCKET_NAME']
        key = self.build_s3_key()
        response = s3.get_object(Bucket=bucket_name, Key=key)
        return response['Body'].read()

    def get_all_metadata_name_for_publisher(self):
        bucket_name = app.config['S3_BUCKET_NAME']
        keys = []
        prefix = self.build_s3_prefix()
        for ob in s3.list_objects(Bucket=bucket_name, Prefix=prefix)['Contents']:
            keys.append(ob['Key'])
        return keys

    def build_s3_key(self):
        return "{prefix}/{publisher}/{package}/_v/{version}/datapackage.json"\
            .format(prefix=self.prefix, publisher=self.publisher,
                    package=self.package, version=self.version)

    def build_s3_prefix(self):
        return "{prefix}/{publisher}".format(prefix=self.prefix, publisher=self.publisher)

    def generate_pre_signed_put_obj_url(self):
        bucket_name = app.config['S3_BUCKET_NAME']
        key = self.build_s3_key()
        params = {'Bucket': bucket_name, 'Key': key}
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


class MetaDataDB(db.Model):
    __tablename__ = "packages"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    publisher = db.Column(db.String(64), unique=True)
    descriptor = db.Column(db.JSON)
    status = db.Column(db.String(16))
    private = db.Column(db.Boolean)

    def __init__(self, name, publisher, descriptor, status, private):
        self.name = name
        self.publisher = publisher
        self.descriptor = descriptor
        self.status = status
        self.private = private
