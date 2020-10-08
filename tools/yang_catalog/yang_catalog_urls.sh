#!/bin/bash
#
# Generates a list of URLs to the online YANG Catalog for the
# given YANG models path. Script can be run from any working
# directory.
#
# Examples:
#    $ ./tools/yang_catalog_urls.sh vendors/cisco/xe/1651
#

# get the script's directory (allow to be called from anywhere)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
TOP_DIR=$(cd $SCRIPT_DIR/../..; pwd)

# get the yang directory argument
if [ $# -ne 1 ]; then
   SCRIPT_NAME=`basename "$0"`
   echo ""
   echo "  Usage:"
   echo "     $SCRIPT_NAME <yang-directory>"
   echo ""
   echo "  Example:"
   echo "     $SCRIPT_NAME vendors/cisco/xe/1651"
   echo ""
   exit 1
fi
YANG_DIR=$1

# verify the directory exists
if [ ! -d $YANG_DIR ]; then
   echo ""
   echo "  Directory '${YANG_DIR}' does not exist"
   echo ""
   exit 1
fi

# iterate over the list of yang models in the yang dir
find ${YANG_DIR}/* -maxdepth 0 -type f -name "*.yang" | while read model; do
    # output the yang catalog url
    YANG_FILE=$(basename $model)
    NAME_NO_EXT=$(basename $model | sed -e 's/.yang//')
    echo "https://yangcatalog.org/yang-search/yang_tree/${NAME_NO_EXT}"
done
