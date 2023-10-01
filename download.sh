#! /bin/bash

set -e

URL="https://www.confuzer.cloud/misc/nethackathon/2023/09/"

pushd $1
wget --continue -r -np -l 2 -A.mp4 $URL
popd
