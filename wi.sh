#!/bin/bash

# DO NOT FORGET to update requirement.txt after pip install <someRequiredPackage>
# pip freeze >requirements.txt


MYDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

if [[ ! -d yab.env ]]
then
	echo "Will buil python virtual env for YAB project"
	virtualenv ${MYDIR}/yab.env
	source ${MYDIR}/yab.env/bin/activate
	pip install -r requirements.txt
else 
	source ${MYDIR}/yab.env/bin/activate
fi

	