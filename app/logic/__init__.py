# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import json

from BeautifulSoup import BeautifulSoup
from flask import current_app as app
from app.utils.helpers import text_to_markdown, dp_in_readme
from app.package.models import BitStore
from app.profile.models import Publisher
from app.search.models import DataPackageQuery

# TODO: authz
def get_package(publisher, package):

    url = '/api/package/%s/%s' % (publisher, package)
    resp = app.test_client().get(url)

    if resp.status_code == 404:
        return None

    metadata = json.loads(resp.data)

    descriptor = metadata.get('descriptor')
    readme = metadata.get('readme')
    descriptor['owner'] = publisher
    readme_variables_replaced = dp_in_readme(readme, descriptor)
    descriptor["readme"] = text_to_markdown(readme_variables_replaced)

    dataViews = descriptor.get('views') or []

    bitstore = BitStore(publisher, package)
    datapackage_json_url_in_s3 = bitstore.build_s3_object_url('datapackage.json')
    readme_short_markdown = text_to_markdown(metadata.get('readme', ''))
    readme_short = ''.join(BeautifulSoup(readme_short_markdown).findAll(text=True)) \
        .split('\n\n')[0].replace(' \n', '') \
        .replace('\n', ' ').replace('/^ /', '')

    datapackage = dict(
        descriptor=descriptor,
        datapackag_url=datapackage_json_url_in_s3,
        views=dataViews,
        short_readme=readme_short
    )

    return datapackage
