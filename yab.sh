
source /usr/local/bin/virtualenvwrapper.sh

MYDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

workon yab;
python ${MYDIR}/yab.py $*
deactivate

