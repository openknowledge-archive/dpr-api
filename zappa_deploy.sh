#!/usr/bin/env bash
current_path=`pwd`
mkdir ~/.aws
python ${current_path}/zappa_set_env.py
status=`zappa update stage -s ${current_path}/zappa_settings_deploy.json`
echo ${status}
if [[ ${status} == *"already deployed"* ]]
then
    zappa deploy stage -s ${current_path}/zappa_settings_deploy.json
fi