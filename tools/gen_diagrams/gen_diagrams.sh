#!/bin/bash
#
# Script that generates UML diagrams (png, svg) and text tree
# diagrams for each Cisco YANG model. The Cisco YANG models are
# segmented by OS type (NX-OS, IOS-XE, IOS-XR) and OS version
# (ie: 16.12.1).
#

# get the script's directory (allow to be called from anywhere)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
TOP_DIR=$(cd $SCRIPT_DIR/../..; pwd)
TOOLS_DIR=$SCRIPT_DIR/tools
PLANTUML_DIR=$TOOLS_DIR/plantuml

# global vars
PLANTUML_CMD="java -DPLANTUML_LIMIT_SIZE=8192 -Djava.awt.headless=true -jar ${PLANTUML_DIR}/plantuml.1.2018.5.jar -quiet"
VENDOR_DIR=$TOP_DIR/vendor
OS_DIRS=(
    $VENDOR_DIR/cisco/xe
    #$VENDOR_DIR/cisco/nx
    #$VENDOR_DIR/cisco/xr
)

# install dependencies
echo "Installing python dependencies..."
virtualenv $SCRIPT_DIR/venv
source $SCRIPT_DIR/venv/bin/activate
pip install -q -r $SCRIPT_DIR/requirements.txt

# iterate over each os directory
for os_dir in "${OS_DIRS[@]}"; do
    # iterate over the list of version dirs in this os dir
    find ${os_dir}/* -maxdepth 0 -type d | while read ver_dir; do
        # iterate over the list of yang models in this os version dir
        find ${ver_dir}/* -maxdepth 0 -type f -name "*.yang" | while read model; do
            PARENT_DIR=$(dirname "$model")
            NAME_NO_EXT=$(basename $model | sed -e 's/.yang//')

            # generate a tree text diagram for the model
            TREE_DIAG=$PARENT_DIR/$NAME_NO_EXT.tree.txt
            echo "Generating text tree diagram '$TREE_DIAG'..."
            YANG_INSTALL=. pyang --path $PARENT_DIR -f tree --tree-print-groupings $model > $TREE_DIAG

            # generate the uml text for the model
            #UML_FILE=$PARENT_DIR/$NAME_NO_EXT.uml
            #echo "Generating UML text for YANG model '$NAME_NO_EXT'..."
            #YANG_INSTALL=. pyang --path $PARENT_DIR -f uml $model -o $UML_FILE

            ## generate the uml diagram images
            #for ext in png svg; do
            #    echo "Generating UML diagram '$NAME_NO_EXT.$ext'..."
            #    $PLANTUML_CMD $UML_FILE -t${ext} >/dev/null 2>&1
            #done
        done
    done
done
