## DPR-API

Requirement python 2.7

```
$ virtualenv env
$ source env/bin/activate
For dev use 
$ pip install -r requirements.dev.txt
else
$ pip install -r requirements.txt
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
aws_access_key_id=
aws_secret_access_key=
aws_region=
```
    
## Testing:
All tests are in tests directory. We use nose for testing

To run all tests plz use ```nosetests tests``` from the base directory.
If want to run specific module use i.e. ```nosetests tests/test_basics.py```

* Some times nosetests got chached by bash so tests may fail as it points to /usr/local/nosetests
 not the virtual env nosetest
 then plz run ```./env/bin/nosetests tests```