
# This script will generate the host key pairs, to avoid false corruption detection in case of infrastructure rebuild.
#


function usage {
	echo 'keygen_host.sh --id <dzrXXX>'
}

while [[ $# > 0 ]]
do
	case $1 in
		--id)
			ID=$2
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

if [ "$ID" = "" ]; then echo "Missing --id parameters"; usage; exit 1; fi


if [ ! -d ./keys ]
then
	mkdir keys
fi


if [ ! -s ./keys/host_${ID} ]
then
	echo "Generate ./keys/host_${ID}"
	ssh-keygen -t rsa  -C "${ID}" -f ./keys/host_${ID}
fi





