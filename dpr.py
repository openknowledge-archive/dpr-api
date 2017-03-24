# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals
import os

from app import create_app

application = create_app()

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    application.run(port=port, host='0.0.0.0')
