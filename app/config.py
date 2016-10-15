class BaseConfig(object):
    DEBUG = False
    TESTING = False
    SWAGGER = {
        "swagger_version": "2.0",
        "title": "DPR API",
        "specs": [
            {
                "version": "0.0.1",
                "title": "v1",
                "endpoint": 'spec',
                "description": "First Cut for DPR API",
                "route": '/spec',
                "rule_filter": lambda rule: True
            }
        ]
    }


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    TESTING = True
    S3_BUCKET_NAME = 'dev'
