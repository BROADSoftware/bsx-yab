#!/bin/bash

set -e


SSH_OPTIONS=-t

MYDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source $MYDIR/functions.sh

if [ "$INFRA_DOMAIN" = "" ]; then echo "INFRA_DOMAIN environment variable must be set"; exit 1; fi

function usage {
	echo 'attachInterface --host <host> --name <VM_name> --bridge <Network_Bridge> --mac <MAC_Address>'
}

while [[ $# > 0 ]]
do
	case $1 in
		--name)
			NAME=$2
			shift
		;;
		--bridge)
			BRIDGE=$2
			shift
		;;
		--host)
			HOST="$2.${INFRA_DOMAIN}"
			shift
		;;
		--mac)
			MAC=$2
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
if [ "$BRIDGE" = "" ]; then echo "Missing --bridge parameters";	usage; exit 1; fi
if [ "$HOST" = "" ]; then echo "Missing --host parameters";	usage; exit 1; fi
if [ "$MAC" = "" ]; then echo "Missing --mac parameters"; usage; exit 1; fi

ssh $SSH_OPTIONS $HOST "sudo virsh attach-interface --domain ${NAME} --type bridge --source ${BRIDGE} --model virtio --mac $MAC --persistent"



