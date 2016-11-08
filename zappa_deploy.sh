#!/usr/bin/env bash
current_path=`pwd`
mkdir ~/.aws
python ${current_path}/zappa_set_env.py
status=`zappa update stage -s ${current_path}/zappa_settings_deploy.json`
echo ${status}
if [[ ${status} == *"Error!"* ]]
then
    zappa deploy stage -s ${current_path}/zappa_settings_deploy.json
fi
zappa unschedule stage -s ${current_path}/zappa_settings_deploy.json
zappa schedule stage -s ${current_path}/zappa_settings_deploy.json

status=`zappa update stage_s3 -s ${current_path}/zappa_settings_deploy.json`
echo ${status}
if [[ ${status} == *"Error!"* ]]
then
    zappa deploy stage_s3 -s ${current_path}/zappa_settings_deploy.json
fi
zappa unschedule stage_s3 -s ${current_path}/zappa_settings_deploy.json
zappa schedule stage_s3 -s ${current_path}/zappa_settings_deploy.json
