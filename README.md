## DPR-API

[![Build Status](https://travis-ci.org/frictionlessdata/dpr-api.svg?branch=master)](https://travis-ci.org/frictionlessdata/dpr-api)
[![Coverage Status](https://coveralls.io/repos/github/frictionlessdata/dpr-api/badge.svg?branch=master)](https://coveralls.io/github/frictionlessdata/dpr-api?branch=master)

## Installation (for Developers)

Requires python 2.7

```
pip install -r requirements.txt

# tests - install additional dependencies
pip install -r requirements.test.txt

# if you encounter errors with psycopg2 you may need to install it manually
sudo apt-get install libpq-dev python-dev
pip install psycopg2
```

### Submodules

The javascript portion of the app comes from a different repo. That repo must
be submoduled in and then built.

```
git submodule init
git submodule update
```

### Database

Create a postgres database

```
$ psql -U postgres -c "create user dpr_user password 'secret' createdb;"
$ psql -U postgres -c "create database dpr_db owner=dpr_user;"

# create tables
python manager.py db upgrade
```

### Environment Configuration

Rename the env.template file to .env file and edit it.

TODO: guidance about this including how to use the DB you created in the
previous step.

### Running locally

You can now run the app locally! To do, run:

```
python dpr.py
```

## Testing

Before running tests run:

```
$ export FLASK_CONFIGURATION=test
```

This ensures that tests are not dependent on any env variable. By default it is dependent on
local postgresql instance.

TODO: explain how to set up this postgresql instance.

We use pytest for testing. All tests are in tests directory. To run the tests do:

```
pytest tests
```

## Continuous deployment process

```
git pull origin master
git checkout deploy
# if you do not yet have the deploy branch
git checkout -b deploy
git merge master
git push origin deploy
```
