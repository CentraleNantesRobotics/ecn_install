#!/usr/bin/env bash

# ACADOS_VERSION=v0.4.0
ACADOS_ROOT=/opt/ecn/acados
ACADOS_SRC=${ACADOS_ROOT}/src
ACADOS_BUILD=${ACADOS_ROOT}/build
ACADOS_INSTALL=${ACADOS_ROOT}/install
TERA_RENDERER=0.0.34


if [[ "$*" == *"-c"* ]]; then
    # check
    # should return old / installed / absent
    if [[ -e ${ACADOS_SRC} ]];then
        cd $ACADOS_SRC
        ver_ok=$(git status | grep -c ${ACADOS_VERSION})
        if [[ -z $ver_ok ]];then
            echo "old"
        else
            echo "installed"
        fi
    else
        echo "absent"
    fi
fi

if [[ "$*" == *"-r"* ]]; then
    # remove
    pip3 uninstall acados
    rm -rf ${ACADOS_ROOT}
fi

if [[ "$*" == *"-i"* ]]; then
    # install / update
    mkdir -p $ACADOS_BUILD
    cd $ACADOS_ROOT
    if [[ -e ${ACADOS_SRC} ]];then
        (cd ${ACADOS_SRC}; git pull --recurse-submodules)
    else
        git clone --recursive https://github.com/acados/acados.git src
    fi

    cd ${ACADOS_BUILD}
    cmake ../src -DACADOS_WITH_OPENMP=ON \
             -DACADOS_WITH_DAQP=ON \
             -DACADOS_WITH_QPOASES=OFF \
             -DACADOS_WITH_HPMPC=OFF \
             -DBLASFEO_EXAMPLES=OFF \
             -DACADOS_INSTALL_DIR=${ACADOS_INSTALL} \
             -DCMAKE_POLICY_VERSION_MINIMUM=3.5

    make -j4 && make install

    # pip3 install -e ${ACADOS_SRC}/interfaces/acados_template --break-system-packages
    # pip3 install -e ${ACADOS_SRC}/interfaces/acados_template

    mkdir -p ${ACADOS_INSTALL}/bin
    wget https://github.com/acados/tera_renderer/releases/download/v${TERA_RENDERER}/t_renderer-v${TERA_RENDERER}-linux \
        -O ${ACADOS_INSTALL}/bin/t_renderer
    chmod +x ${ACADOS_INSTALL}/bin/t_renderer

    # add ACADOS path
    if [[ $(grep -c ACADOS /etc/bash.bashrc) -eq 0 ]]; then
        sudo echo "export ACADOS_SOURCE_DIR=${ACADOS_INSTALL}" >> /etc/bash.bashrc
        sudo echo "export LD_LIBRARY_PATH=\${LD_LIBRARY_PATH}:\${ACADOS_SOURCE_DIR}/lib" >> /etc/bash.bashrc
    fi
fi
