# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

from app import create_app
from app.profile.models import *
from flask_marshmallow import Marshmallow

app = create_app()
ma = Marshmallow(app)

class PublisherSchema(ma.ModelSchema):
    class Meta:
        model = Publisher

class UserSchema(ma.ModelSchema):
    class Meta:
        model = User

class PublisherUserSchema(ma.ModelSchema):
    class Meta:
        model = PublisherUser
