# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import re
import sqlalchemy
from sqlalchemy import or_
from app.package.models import Package
from app.profile.models import Publisher


class DataPackageQuery(object):

    def __init__(self, query_string, limit=None):
        self.query_string = query_string
        try:
            self.limit = min(int(limit), 1000)
        except (ValueError, TypeError):
            self.limit = 20

    def _build_sql_query(self, query, query_filters):

        sql_query = Package.query.join(Package.publisher)
        sa_filters = []
        for f in query_filters:
            filter_class, filter_term = f.split(":")
            if filter_class == 'publisher':
                sa_filters.append(Publisher.name == filter_term)
            else:
                raise Exception("not supported any other filter right now")
        if len(sa_filters) > 0:
            sql_query = sql_query.filter(or_(*sa_filters))

        if query != '*' or not query.strip():
            sql_query = sql_query.filter(Package.descriptor.op('->>')
                                         ('title').cast(sqlalchemy.TEXT)
                                         .ilike("%{q}%".format(q=query)))

        return sql_query

    def _parse_query_string(self):

        regex = "(\\b\\w+\\b:[\\-\\w\\_\\@]+)"
        copy = self.query_string
        qu_filters, qu = [], ''
        for match in re.findall(regex, copy):
            qu_filters.append(match)
            copy = copy.replace(match, ":")
        for qs in copy.split(":"):
            if qs.strip():
                qu = qs.strip()
                break
        return qu, qu_filters

    def get_data(self):
        data_list = []
        q, qf = self._parse_query_string()

        results = self._build_sql_query(q, qf).limit(self.limit)

        for result in results:
            data = result.__dict__
            data['descriptor'] = data['descriptor']
            data['status'] = data['status'].value
            p = result.publisher
            data['publisher_name'] = p.name
            if '_sa_instance_state' in data:
                data.pop('_sa_instance_state', None)

            data_list.append(data)
        for data in data_list:
            if 'publisher' in data:
                data.pop('publisher', None)
        return data_list
