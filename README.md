## DPR-API

[![Build Status](https://travis-ci.org/frictionlessdata/dpr-api.svg?branch=master)](https://travis-ci.org/frictionlessdata/dpr-api)
[![Coverage Status](https://coveralls.io/repos/github/frictionlessdata/dpr-api/badge.svg?branch=master)](https://coveralls.io/github/frictionlessdata/dpr-api?branch=master)


Requirement python 2.7

```
$ virtualenv env
$ source env/bin/activate
For dev use 
$ pip install -r requirements.dev.txt
else
$ pip install -r requirements.txt
```
### Set up postgres database

```
$ psql -U postgres -c "create user dpr_user password 'secret' createdb;"
$ psql -U postgres -c "create database dpr_db owner=dpr_user;"

# create and populate tables
$ python manager.py createdb
$ python manager.py populate

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
    $ zappa deploy dev [This is for first time deployment]
    
    For further deployment:
    $  zappa update dev

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
    
## Environment Setting:
Plz put .env file in root directory and add environment variables to that
```
API_KEY=
AWS_ACCESS_KET_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=
AUTH0_CLIENT_ID=
AUTH0_CLIENT_SECRET=
AUTH0_DOMAIN=
AUTH0_DB_NAME=
AUTH0_LOGIN_PAGE=
AUTH0_CALLBACK_URL=
S3_BUCKET_NAME=
SQLALCHEMY_DATABASE_URI=
```
Rename the env.template file to .env file.
    
## Testing:
All tests are in tests directory. We use nose for testing

To run all tests plz use ```nosetests tests``` from the base directory.
If want to run specific module use i.e. ```nosetests tests/test_basics.py```

* Some times nosetests got chached by bash so tests may fail as it points to /usr/local/nosetests
 not the virtual env nosetest
 then plz run ```./env/bin/nosetests tests```
