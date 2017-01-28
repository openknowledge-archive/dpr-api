# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

from app import create_app

application = create_app()

if __name__ == "__main__":
    from gevent.wsgi import WSGIServer
    http_server = WSGIServer(('', 5000), application)
    http_server.serve_forever()
