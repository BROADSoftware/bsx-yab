# This script is intended to inject build key in a host which does not already have it.
# (i.e. manually installed, not by kickstart)


function usage {
	echo 'inject_build_key.sh --target <hostname>'
}

while [[ $# > 0 ]]
do
	case $1 in
		--target)
			TARGET=$2
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

if [ "$TARGET" = "" ]; then echo "Missing --target parameters"; usage; exit 1; fi


MYDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

$MYDIR/keygen_build.sh

ansible ${TARGET} -m authorized_key -a "user=root key=\"{{ lookup('file', './keys/build_key.pub')}}\"" -u root --ask-pass

