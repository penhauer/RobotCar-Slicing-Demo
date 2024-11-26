#!/bin/bash

# taken from https://github.com/opencv/opencv-python/issues/530


function install-opencv-python() {
  TMPDIR=$(mktemp -d)
  pushd "${TMPDIR}"

  OPENCV_VER="master"
  # Build and install OpenCV from source.
  git clone --branch ${OPENCV_VER} --depth 1 --recurse-submodules --shallow-submodules https://github.com/opencv/opencv-python.git opencv-python-${OPENCV_VER}
  cd opencv-python-${OPENCV_VER}

  # We want the HEADLESS opencv for GUI stuff
  export ENABLE_HEADLESS=0

  export ENABLE_CONTRIB=0
  # We want GStreamer support enabled.
  export CMAKE_ARGS="-DWITH_GSTREAMER=ON"

  python3 -m pip wheel . --verbose
  python3 -m pip install opencv_python*.whl

  popd
}

if [[ ! -f "./venv/bin/activate" ]]; then
  python3 -m venv venv
  source venv/bin/activate
  pip3 install -r requirements_client.txt
  install-opencv-python
fi

