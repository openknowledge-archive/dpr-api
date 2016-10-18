from flask import current_app as app


class Catalog(object):
    def __init__(self):
        self._list = []
        self._cache = {}
    
    def load(self, datapackages):
        self._list = datapackages
        for dp in datapackages:
            if not dp['owner'] in self._cache:
                self._cache[dp['owner']] = {}
            self._cache[dp['owner']][dp['name']] = dp
    
    def get(self, owner, id):
        if owner in self._cache:
            return self._cache[owner][id]
    
    def query(self):
        return self._list
    
    def by_owner(self, owner):
        result = []
        if owner in self._cache:
            for dp in self._cache[owner]:
                result.append(self._cache[owner][dp])
        return result
