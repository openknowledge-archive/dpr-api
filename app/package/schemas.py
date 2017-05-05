# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

from flask_marshmallow import Marshmallow
from app.package.models import *
from app import create_app

app = create_app()
ma = Marshmallow(app)

class PackageSchema(ma.ModelSchema):
    class Meta:
        model = Package

class PackageTagSchema(ma.ModelSchema):
    class Meta:
        model = PackageTag
