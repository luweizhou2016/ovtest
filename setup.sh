#!/bin/bash

if [ -d "$1" ]; then
  # Take action if $DIR exists. #
  echo "Using openvino source $1..."
else
  echo "Please provide openvino source DIR ."
  exit 1
fi

# openvino source code root
ov_src=`realpath $1`

ln -s $ov_src openvino

mkdir -p extern

cd extern

mkdir -p cv_bench_cache
sudo mount -t nfs -o ro 10.91.242.212:/data/cv_bench_cache ./cv_bench_cache

mkdir -p omz-validation-datasets
sudo mount -t nfs -o ro 10.91.242.212:/data/nn_icv_cv_externalN/omz-validation-datasets ./omz-validation-datasets

#mkdir nfs_share_data
#sudo mount -t nfs -o ro 10.67.107.130:/home/share nfs_share_data

#mkdir nfs_share_models
#sudo mount -t nfs 10.67.108.173:/home/vsi/nfs_share nfs_share_models



python3 -m virtualenv ./venv
. ./venv/bin/activate

pip install -r ../requirements.txt
## install accuracy_checker in-place
pip install -e $ov_src/thirdparty/open_model_zoo/tools/accuracy_checker/

mkdir -p annotations

# complementary repo that provides more annotation converters
git clone git@gitlab-icv.toolbox.iotg.sclab.intel.com:algo/annotation_converters_ext.git &&
cd annotation_converters_ext &&
python3 setup.py install_as_extension --accuracy-checker-dir=$ov_src/thirdparty/open_model_zoo/tools/accuracy_checker

git clone git@github.com:intel-innersource/frameworks.ai.openvino.accuracy-checker-configs.git
