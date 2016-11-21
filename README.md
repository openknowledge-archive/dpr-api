## DPR-API

[![Build Status](https://travis-ci.org/frictionlessdata/dpr-api.svg?branch=master)](https://travis-ci.org/frictionlessdata/dpr-api)
[![Coverage Status](https://coveralls.io/repos/github/frictionlessdata/dpr-api/badge.svg?branch=master)](https://coveralls.io/github/frictionlessdata/dpr-api?branch=master)


Requirement python 2.7

```
$ virtualenv env
$ source env/bin/activate
For test use 
$ pip install -r requirements.txt
$ pip install -r requirements.test.txt
else
$ pip install -r requirements.txt
```

## Environment Setting:
Plz put .env file in root directory and add environment variables to that
```
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=
AUTH0_CLIENT_ID=
AUTH0_CLIENT_SECRET=
AUTH0_DOMAIN=
AUTH0_DB_NAME=
AUTH0_API_AUDIENCE=
S3_BUCKET_NAME=
FLASKS3_BUCKET_NAME=
SQLALCHEMY_DATABASE_URI=
```
Rename the env.template file to .env file.


### Set up postgres database

```
$ psql -U postgres -c "create user dpr_user password 'secret' createdb;"
$ psql -U postgres -c "create database dpr_db owner=dpr_user;"

# create tables
python manager.py db upgrade

# you may need to install psysopg2 manually if comand throws errors
$ sudo apt-get install libpq-dev python-dev
$ pip install psycopg2
```

### DPR API project. 
This is flask based project. We can also deploy this in AWS lambda using zappa.

#### Local Deployment Process: 
For local testing we can start the project using:
    
```
$ python dpr.py
```

#### Lambda Deployment Process:
The lambda configuration is in zappa_settings.json
There are different environment to deploy.

    # Right now only dev env config is there.
    $ zappa deploy stage [This is for first time deployment]
    
    For further deployment:
    $  zappa update stage

##### Zappa Configuration:
```
s3_bucket: Which bucket the zip will be deployed
aws_region: aws region
environment_variables.FLASK_CONFIGURATION what config class the app will take from 
   app.config.py 
```
    
## Api Doc:
All api documentation is maintained by [flasgger](https://github.com/rochacbruno/flasgger)

The swagger UI Url path is {host}/apidocs/index.html
    
## Testing:
Before running tests plz run:
```
$ export FLASK_CONFIGURATION=test
```
. So that tests are not dependent on any env variable. By default it is dependent on
local postgresql instance.

All tests are in tests directory. We use nose for testing

To run all tests plz use ```nosetests tests``` from the base directory.
If want to run specific module use i.e. ```nosetests tests/test_basics.py```

* Some times nosetests got chached by bash so tests may fail as it points to /usr/local/nosetests
 not the virtual env nosetest
 then plz run ```./env/bin/nosetests tests```
