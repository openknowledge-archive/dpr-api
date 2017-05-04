# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import json

from BeautifulSoup import BeautifulSoup
from flask import current_app as app
from app.utils.helpers import text_to_markdown, dp_in_readme
from app.package.models import BitStore, Package, PackageStateEnum
from app.profile.models import Publisher
from app.search.models import DataPackageQuery

# TODO: authz
def get_package(publisher, package):
    '''
    Returns info for package - modified descriptor, bitstore URL for descriptor,
    views and short README
    '''
    metadata = get_metadata_for_package(publisher, package)
    if not metadata:
        return None

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

def get_metadata_for_package(publisher, package):
    '''
    Returns metadata for given package owned by publisher
    '''
    data = Package.query.join(Publisher).\
        filter(Publisher.name == publisher,
               Package.name == package,
               Package.status == PackageStateEnum.active).\
        first()
    if not data:
        return None
    tag = filter(lambda t: t.tag == 'latest', data.tags)[0]
    metadata = dict(
        id = data.id,
        name = data.name,
        publisher = data.publisher.name,
        readme = tag.readme or '',
        descriptor = tag.descriptor
    )
    return metadata
