#!/usr/bin/env bash
current_path=`pwd`
export AWS_CONFIG_FILE=${current_path}/.credentials
mkdir /root/.aws
python ${current_path}/zappa_set_env.py
status=`zappa update stage -s ${current_path}/zappa_settings_deploy.json`
echo ${status}
if [[ ${status} == *"already deployed"* ]]
then
    zappa deploy stage -s ${current_path}/zappa_settings_deploy.json
fi