#!/bin/bash

set -e


SSH_OPTIONS=-t

MYDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

source ./setenv.sh

function usage {
	echo 'attachDisk --host <host> --name <VM_name> --size <Disk_size_in_GB> --volume <Volume(vol0-4)> --device <vd[a-x])'
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
		--size)
			SIZE=$2
			shift
		;;
		--volume)
			VOLUME=$2
			shift
		;;
		--device)
			DEVICE=$2
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
if [ "$SIZE" = "" ]; then echo "Missing --size parameters";	exit 1; fi
if [ "$VOLUME" = "" ]; then echo "Missing --volume parameters";	exit 1; fi
if [ "$DEVICE" = "" ]; then echo "Missing --device parameters";	exit 1; fi

DISK_IMG=${VOLUME}/libvirt/images/${NAME}_${DEVICE}.qcow2


set -x
ssh $SSH_OPTIONS $HOST "qemu-img create -f qcow2 -o preallocation=metadata ${DISK_IMG} ${SIZE}G"

ssh $SSH_OPTIONS $HOST "fallocate -l ${SIZE}G ${DISK_IMG}"

ssh $SSH_OPTIONS $HOST "virsh attach-disk --domain ${NAME} --source ${DISK_IMG} --target ${DEVICE} --persistent --driver qemu --subdriver qcow2 --type disk --sourcetype file"



