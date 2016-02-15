
# This script will generate the buid key pair which will allow root access for ansible


if [ ! -d ./keys ]
then
	mkdir keys
fi

if [ ! -s ./keys/build_key ]
then
	echo "Generate ./keys/build_key"
	ssh-keygen -t rsa -C "build_from_$(pwd)" -f ./keys/build_key
else 
	echo "./keys/build_key already generated"
fi




