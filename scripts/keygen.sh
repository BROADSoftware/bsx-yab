
# This script will generate a buid key pair


KP=$1


function usage {
	echo 'USAGE: keygen.sh  <key_path>'
}


if [ "$KP" = "" ]; then echo "Missing full key path parameters"; usage; exit 1; fi

DIR=$(dirname $KP)


if [ ! -d $DIR ]
then
	mkdir $DIR
fi

if [ ! -s $KP ]
then
	echo "Generate $KP"
	ssh-keygen -t rsa -C "build_from_$(pwd)" -f $KP
else 
	echo "$KP already generated"
fi




