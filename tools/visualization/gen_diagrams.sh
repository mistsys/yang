#!/bin/bash
#
# Script that generates the following for each YANG model...
# 1) UML diagram (png image)
# 2) UML diagram (svg image)
# 3) Tree text diagram
#
# Mark Craig
# mark@mist.com
#

# get the script's directory (allow to be called from anywhere)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
TOP_DIR=$(cd $SCRIPT_DIR/../..; pwd)

# global vars
TOOLS=$TOP_DIR/tools
IMAGES=$TOP_DIR/images
VENDOR=$TOP_DIR/vendor
PLANTUML_CMD="java -DPLANTUML_LIMIT_SIZE=8192 -jar ${TOOLS}/plantuml/plantuml.1.2018.5.jar -quiet"
MODEL_DIRS=(
    $VENDOR/cisco/xe/16101
)

# install dependencies
echo "Installing python dependencies..."
virtualenv $TOOLS/venv
source $TOOLS/venv/bin/activate
pip install -q -r $SCRIPT_DIR/requirements.txt

# generate diagrams for each openconfig model
for model_dir in "${MODEL_DIRS[@]}"; do
    # create the model's image output directory (if needed)
    IMAGES_OUT_DIR=$IMAGES/${model_dir#*$TOP_DIR/}
    if [ ! -d $IMAGES_OUT_DIR ]; then
        mkdir -p $IMAGES_OUT_DIR
    fi

    # for each yang model in the base directory
    for model in `find $model_dir -type f -name "*.yang"`; do
        # build the base output path
        SHORT_PATH=${model#*$TOP_DIR/}
        OUT_BASE_PATH=$IMAGES/${SHORT_PATH%.yang}
        OUT_DIR=$IMAGES/$(dirname "${SHORT_PATH}")

        # generate the uml text for the model
        BASENAME=`basename $model | sed -e 's/.yang//'`
        echo "Generating UML text for model '$BASENAME' model..."
        INCLUDE_PATHS=$model_dir:$model_dir/MIBS:$model_dir/cbr:$model_dir/isr4k:$model_dir/cat9k
        pyang --path $INCLUDE_PATHS -f uml $model -o $OUT_BASE_PATH.uml >/dev/null 2>&1

        # generate the uml diagram images
        for ext in png svg; do
            echo "Generating UML diagram '$BASENAME.$ext' for '$BASENAME' model..."
            $PLANTUML_CMD $OUT_BASE_PATH.uml -t${ext} -o $OUT_DIR/
        done

        # generate a tree text diagram for the model
        echo "Generating text tree '$BASENAME.tree.txt' for '$BASENAME' model..."
        pyang --path $INCLUDE_PATHS -f tree $model > $OUT_BASE_PATH.tree.txt

        # cleanup
        mv $OUT_DIR/img/* $OUT_DIR/
        rmdir $OUT_DIR/img
    done
done
