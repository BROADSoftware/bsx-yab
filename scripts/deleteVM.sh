#!/bin/bash

set +e


SSH_OPTIONS="-t -t -q"

MYDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

if [ "$INFRA_DOMAIN" = "" ]; then echo "INFRA_DOMAIN environment variable must be set"; exit 1; fi
if [ "$COBBLER_HOST" = "" ]; then echo "COBBLER_HOST environment variable must be set"; exit 1; fi

function usage {
	echo 'stopVM --host <host> --name <VM_name>'
}

while [[ $# > 0 ]]
do
	case $1 in
		--name)
			NAME=$2
			shift
		;;
		--host)
			HOST="$2.${INFRA_DOMAIN}"
			shift
		;;
		*)
			echo "Unknown parameter $1"
			usage
			exit 1
		;;
	esac
	shift
done

if [ "$NAME" = "" ]; then echo "Missing --name parameters"; usage; exit 1; fi
if [ "$HOST" = "" ]; then echo "Missing --host parameters";	usage; exit 1; fi

echo "Deleting the VM ${NAME}"

# ssh $SSH_OPTIONS $HOST "sudo virsh destroy ${NAME}"
ssh $SSH_OPTIONS $HOST "sudo virsh undefine ${NAME}"

ssh $SSH_OPTIONS $COBBLER_HOST "sudo cobbler system remove  --name=${NAME}


