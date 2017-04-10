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
$ python manager.py createdb
$ python manager.py populate
```

While development, if you make changes to database structure, Eg: added new table,
renamed column etc... You will have to **drop** all the tables and recreate them

```
$ python manager.py dropdb
$ python manager.py createdb
$ python manager.py populate
```

Note: Be careful! Doing so **all** of you data will be erased. **Never, ever** run
`python manager.py dropdb` on production database like RDS or any other, unless you
are super confident what are you doing!

### Environment Configuration

Rename the env.template file to .env file and edit it.

```
JWT_SEED=<<Super Secret Key For Flask Sessions>>
SQLALCHEMY_DATABASE_URI=<<Postgres Database URI>>*
S3_BUCKET_NAME=<<AWS S3 Bucket Name For Data Storage>>
AWS_ACCESS_KEY_ID= <<AWS Access Key>>
AWS_SECRET_ACCESS_KEY= <<AWS Secret Access Key>>
AWS_REGION= <<AWS Region >>
GITHUB_CLIENT_ID= <<Github Client ID>>
GITHUB_CLIENT_SECRET= <<Github Client Secret>>

# For Deploy
PROJECT= <<Project Name>>
DOMAIN_BASE= <<Domain Base. Eg: example.com>>
STAGE=<<Project Stage. Eg: dev>>
DOMAIN=<<Full Domain. Eg: dev.example.com>>
DPR_API_GIT=<<Git URL For Repo>>
```

For local development you can leave empty all variables except following ones:

- SQLALCHEMY_DATABASE_URI
- JWT_SEED
- AWS_REGION
- GITHUB_CLIENT_ID
- GITHUB_CLIENT_SECRET

You can use any string you like, Eg: "development", for all of them, except `SQLALCHEMY_DATABASE_URI`

SQLALCHEMY_DATABASE_URI should follow the general form for a postgresq connection URI:
`postgres://[user[:password]@][netloc][:port][/dbname][?param1=value1&...]`

If you created postgres database by following our instructions above, it should look like this:

`SQLALCHEMY_DATABASE_URI=postgres://dpr_user:secret@localhost/dpr_db`

### Running locally

You can now run the app locally! To do, run:

```
$ python dpr.py
```

## Testing

Before running tests run:

```
$ export FLASK_CONFIGURATION=test
```

This ensures that tests are not dependent on any env variable. By default it is dependent on
local postgresql instance.

You would want to create separate database for tests, for not loosing all the data
from development database, you are working with.

```
$ psql -U postgres -c "create database dpr_test_db owner=dpr_user;"
```

We use pytest for testing. All tests are in tests directory. To run the tests do:

```
$ pytest tests
```
