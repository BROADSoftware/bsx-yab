#!/bin/bash
# Script to create a VM on a kvm based infrastructure
# Handle Cobbler registration, root disk and VM creation
#

set -e
set +x

SSH_OPTIONS="-t -t -q"

MYDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source $MYDIR/functions.sh

if [ "$INFRA_DOMAIN" = "" ]; then echo "INFRA_DOMAIN environment variable must be set"; exit 1; fi
if [ "$COBBLER_HOST" = "" ]; then echo "COBBLER_HOST environment variable must be set"; exit 1; fi


function usage {
	echo 'createVM --host <host> --name <VM_name> --ram <Memory_in_GB> --vcpu <Nbr_Vcpu> --disk <Disk_size_in_GB> --volume <Volume(vol0-4)> --hostname <VM_hostname> \
		 --bridge <Network_Bridge> --ip <IP_Address> --netmask <Netmask> --gateway <Gateway> --mac <MAC_Address> --buildkey <BuildKeyPath> --hostkey <HostKeyPath> --dns <dn1 dns2 ...>'
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
		--ram)
			RAM=$(expr $2 \* 1024)
			shift
		;;
		--vcpu)
			VCPU=$2
			shift
		;;
		--disk)
			DISK=$2
			shift
		;;
		--volume)
			VOLUME=$2
			shift
		;;
		--hostname)
			VM_HOSTNAME=$2
			shift
		;;
		--bridge)
			BRIDGE=$2
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
if [ "$RAM" = "" ]; then echo "Missing --ram parameters"; usage; exit 1; fi
if [ "$HOST" = "" ]; then echo "Missing --host parameters";	usage; exit 1; fi
if [ "$VCPU" = "" ]; then echo "Missing --vcpu parameters";	exit 1; fi
if [ "$DISK" = "" ]; then echo "Missing --disk parameters";	exit 1; fi
if [ "$VOLUME" = "" ]; then echo "Missing --volume parameters";	exit 1; fi
if [ "$VM_HOSTNAME" = "" ]; then echo "Missing --hostname parameters"; usage; exit 1; fi
if [ "$BRIDGE" = "" ]; then echo "Missing --bridge parameters"; usage; exit 1; fi
if [ "$IP" = "" ]; then echo "Missing --ip parameters"; usage; exit 1; fi
if [ "$NETMASK" = "" ]; then echo "Missing --netmask parameters"; usage; exit 1; fi
if [ "$GATEWAY" = "" ]; then echo "Missing --gateway parameters"; usage; exit 1; fi
if [ "$MAC" = "" ]; then echo "Missing --mac parameters"; usage; exit 1; fi
if [ "$BUILDKEY" = "" ]; then echo "Missing --buildkey parameters"; usage; exit 1; fi
if [ "$HOSTKEY" = "" ]; then echo "Missing --hostkey parameters"; usage; exit 1; fi
if [ "$DNS" = "" ]; then echo "Missing --dns parameters"; usage; exit 1; fi


DSK=/${VOLUME}/libvirt/images/${NAME}_vda.qcow2

# Ensure we will not overwrite an existing one

set +e
ensure_ip_free $IP

ssh $SSH_OPTIONS $HOST "ls $DSK" >/dev/null
if [ $? -eq 0 ]; then echo "DISK ${DSK} ALREADY EXISTING ON ${HOST}!!!. WILL STOP"; exit 1; fi 
set -e

# Ok, let's go

scp $BUILDKEY.pub $COBBLER_HOST:/tmp/build_key_pub_${NAME}
ssh $SSH_OPTIONS $COBBLER_HOST "sudo mv /tmp/build_key_pub_${NAME} /var/lib/cobbler/snippets/per_system/build_key_pub/${NAME}"

scp $HOSTKEY $COBBLER_HOST:/tmp/host_key_priv_${NAME}
ssh $SSH_OPTIONS $COBBLER_HOST "sudo mv /tmp/host_key_priv_${NAME} /var/lib/cobbler/snippets/per_system/host_key_priv/${NAME}"

scp $HOSTKEY.pub $COBBLER_HOST:/tmp/host_key_pub_${NAME}
ssh $SSH_OPTIONS $COBBLER_HOST "sudo mv /tmp/host_key_pub_${NAME} /var/lib/cobbler/snippets/per_system/host_key_pub/${NAME}"


# Note than some parameters (ram, vcpu, disk) are for reference information accuracy, as not directly used at this level (We don't use koan)
ssh $SSH_OPTIONS $COBBLER_HOST "sudo cobbler system add --clobber --name=${NAME} --profile=centos7-kvm --hostname=${VM_HOSTNAME} --static=1 --interface=eth0 --ip-address=${IP} \
    --netmask=${NETMASK} --gateway=${GATEWAY} --mac=${MAC} --virt-ram=${RAM} --virt-cpus=${VCPU} --virt-file-size=${DISK} --virt-bridge=${BRIDGE} --name-servers=${DNS} --name-servers-search=${INFRA_DOMAIN}"

ssh $SSH_OPTIONS $HOST "sudo qemu-img create -f qcow2 -o preallocation=metadata $DSK ${DISK}G"

ssh $SSH_OPTIONS $HOST "sudo fallocate -l ${DISK}G /${VOLUME}/libvirt/images/${NAME}_vda.qcow2"

ssh $SSH_OPTIONS $HOST "sudo virt-install -n ${NAME} -r ${RAM} --vcpus=${VCPU}  --network bridge=${BRIDGE},model=virtio,mac=${MAC} --disk path=$DSK \
		 --pxe --accelerate --vnc --os-type=linux --os-variant=rhel7 --noreboot"
		 
echo "Waiting for the VM  $NAME to shutdown"

wait_shutdown $HOST $NAME "Waiting $NAME down\n"		

echo "Mark as autostart"
ssh $SSH_OPTIONS $HOST "sudo virsh autostart ${NAME}"

echo "$NAME built and halted"


