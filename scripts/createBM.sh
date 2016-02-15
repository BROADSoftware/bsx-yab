#!/bin/bash
#
# Script to register a Bare Metal system in cobbler
#

set -e
set +x

SSH_OPTIONS="-t -t -q"

MYDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source $MYDIR/functions.sh

source ./setenv.sh


function usage {
	echo 'createBM --name <nameForCobbler> --hostname <hostname>  --device <ethDevice> --ip <IP_Address> --netmask <Netmask> --gateway <Gateway> --mac <MAC_Address> --buildkey <BuildKeyPath> --hostkey <HostKeyPath> --dns <dn1 dns2 ...>'
}

while [[ $# > 0 ]]
do
	case $1 in
		--name)
			NAME=$2
			shift
		;;
		--hostname)
			HOSTNAME=$2
			shift
		;;
		--device)
			DEVICE=$2
			shift
		;;
		--ip)
			IP=$2
			shift
		;;
		--netmask)
			NETMASK=$2
			shift
		;;
		--gateway)
			GATEWAY=$2
			shift
		;;
		--mac)
			MAC=$2
			shift
		;;
		--buildkey)
			BUILDKEY=$2
			shift
		;;
		--hostkey)
			HOSTKEY=$2
			shift
		;;
		--dns)
			DNS=$2
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
if [ "$HOSTNAME" = "" ]; then echo "Missing --hostname parameters"; usage; exit 1; fi
if [ "$DEVICE" = "" ]; then echo "Missing --device parameters"; usage; exit 1; fi
if [ "$IP" = "" ]; then echo "Missing --ip parameters"; usage; exit 1; fi
if [ "$NETMASK" = "" ]; then echo "Missing --netmask parameters"; usage; exit 1; fi
if [ "$GATEWAY" = "" ]; then echo "Missing --gateway parameters"; usage; exit 1; fi
if [ "$MAC" = "" ]; then echo "Missing --mac parameters"; usage; exit 1; fi
if [ "$BUILDKEY" = "" ]; then echo "Missing --buildkey parameters"; usage; exit 1; fi
if [ "$HOSTKEY" = "" ]; then echo "Missing --hostkey parameters"; usage; exit 1; fi
if [ "$DNS" = "" ]; then echo "Missing --dns parameters"; usage; exit 1; fi

scp $BUILDKEY.pub $COBBLER_HOST:/tmp/build_key_pub_${NAME}
ssh $SSH_OPTIONS $COBBLER_HOST "sudo mv /tmp/build_key_pub_${NAME} /var/lib/cobbler/snippets/per_system/build_key_pub/${NAME}"

scp $HOSTKEY $COBBLER_HOST:/tmp/host_key_priv_${NAME}
ssh $SSH_OPTIONS $COBBLER_HOST "sudo mv /tmp/host_key_priv_${NAME} /var/lib/cobbler/snippets/per_system/host_key_priv/${NAME}"

scp $HOSTKEY.pub $COBBLER_HOST:/tmp/host_key_pub_${NAME}
ssh $SSH_OPTIONS $COBBLER_HOST "sudo mv /tmp/host_key_pub_${NAME} /var/lib/cobbler/snippets/per_system/host_key_pub/${NAME}"

ssh $SSH_OPTIONS $COBBLER_HOST "sudo cobbler system add --clobber --name=${NAME} --profile=centos7-bm1 --hostname=${HOSTNAME} --static=1 --interface=${DEVICE}  \
 --gateway=${GATEWAY} --mac=${MAC} --name-servers=${DNS} --name-servers-search=${INFRA_DOMAIN} --ksmeta='interface=${DEVICE}  ip_address=${IP}  netmask=${NETMASK}'"

echo ""
echo "Host ${NAME} registered!"
