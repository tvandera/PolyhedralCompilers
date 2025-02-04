# Base Stage: Common build environment
FROM ubuntu:20.04 AS base

ENV POLYHEDRAL_DIR="/polyhedral"

# Install essential build tools and dependencies
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        build-essential libtool autoconf automake libltdl-dev pkg-config flex bison libgmp-dev \
        clang-9 libclang-9-dev llvm-9 llvm-9-tools llvm-9-dev texinfo ninja-build \
        libxml2-dev ccache ghostscript \
        git wget curl rsync gpg less vim \
        python3 python3-dev python3-pip python3-pandas python3-numpy python3-scipy \
        python3-pybind11 python3-yaml python3-tables \
        libhdf5-dev  libjpeg-dev zlib1g-dev && \
    ln -sf /usr/bin/python3 /usr/bin/python && \
    rm -rf /var/lib/apt/lists/*


RUN wget -O - https://apt.kitware.com/keys/kitware-archive-latest.asc 2>/dev/null | \
        gpg --dearmor - | \
        tee /usr/share/keyrings/kitware-archive-keyring.gpg >/dev/null && \
    echo 'deb [signed-by=/usr/share/keyrings/kitware-archive-keyring.gpg] https://apt.kitware.com/ubuntu/ focal main' | \
        tee /etc/apt/sources.list.d/kitware.list >/dev/null &&  \
    apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends cmake && \
    rm -rf /var/lib/apt/lists/*


# Change default compilers to make Pluto happy.
RUN update-alternatives --install /usr/bin/llvm-config llvm-config /usr/bin/llvm-config-9 100 && \
    update-alternatives --install /usr/bin/FileCheck FileCheck /usr/bin/FileCheck-9 100 && \
    update-alternatives --install /usr/bin/clang clang /usr/bin/clang-9 100 && \
    update-alternatives --install /usr/bin/clang++ clang++ /usr/bin/clang++-9 100

# Stage 2: LLVM and Polly Build
FROM base AS llvm-build
ARG LLVM_TAG="llvmorg-15.0.2"
ARG LLVM_TAR_URL=" https://github.com/llvm/llvm-project/archive/refs/tags/${LLVM_TAG}.tar.gz"
RUN mkdir -p /tmp/build-llvm && \
    cd /tmp/build-llvm && \
    wget -qO - ${LLVM_TAR_URL} | \
    tar xzf - && \
    cmake -G Ninja */llvm \
        -DLLVM_ENABLE_PROJECTS="clang;openmp;polly" \
        -DLLVM_TARGETS_TO_BUILD="X86" \
        -DCMAKE_BUILD_TYPE=Release \
        -DMLIR_ENABLE_BINDINGS_PYTHON=True \
        -DBUILD_SHARED_LIBS=True \
        -DLLVM_USE_LINKER=gold \
        -DCMAKE_INSTALL_PREFIX=/usr/local/polyhedral/polly \
    && \
    ninja all && \
    ninja install && \
    ln -s /usr/local/polyhedral/polly/bin/clang /usr/local/bin/polly-clang

#Polygeist Installation
FROM base as polygeist-build

ARG POLYGEIST_URL="https://github.com/llvm/Polygeist/archive/refs/heads/main-042621.tar.gz"
RUN wget -qO- ${POLYGEIST_URL} | \
    tar xz --one-top-level=/mlir-clang --strip-components 1 && \
    cd /mlir-clang && mkdir build && cd build \
    && cmake -G Ninja ../llvm \
         -DLLVM_ENABLE_PROJECTS="mlir;polly;clang;openmp" \
         -DLLVM_BUILD_EXAMPLES=ON \
         -DLLVM_TARGETS_TO_BUILD="host" \
         -DCMAKE_BUILD_TYPE=Release \
         -DLLVM_ENABLE_ASSERTIONS=ON \
         -DCMAKE_INSTALL_PREFIX=/usr/local/polyhedral/polygeist \
    && ninja all \
    && ninja install

# Install Polymer
FROM base as polymer-build

RUN git clone -b pact --single-branch --recursive https://github.com/kumasento/polymer \
    && cd polymer \
    && git checkout pact \
    && sed -ie 's/git:/https:/g' .gitmodules \
    && git submodule update --recursive --init \
    && mkdir llvm/build \
    && cd llvm/build \
    && cmake ../llvm \
      -DLLVM_ENABLE_PROJECTS="llvm;clang;mlir" \
      -DLLVM_TARGETS_TO_BUILD="host" \
      -DLLVM_ENABLE_ASSERTIONS=ON \
      -DCMAKE_BUILD_TYPE=DEBUG \
      -DLLVM_INSTALL_UTILS=ON \
      -DCMAKE_C_COMPILER=clang \
      -DCMAKE_CXX_COMPILER=clang++ \
      -DCMAKE_INSTALL_PREFIX=/usr/local/polyhedral/polymer \
      -G Ninja \
    && ninja all \
    && ninja install

RUN cd polymer \
    && rm -rf build && mkdir build && cd build \
	&& cmake .. \
		  -DCMAKE_BUILD_TYPE=DEBUG \
		  -DMLIR_DIR=$PWD/../llvm/build/lib/cmake/mlir \
		  -DLLVM_DIR=$PWD/../llvm/build/lib/cmake/llvm \
		  -DLLVM_ENABLE_ASSERTIONS=ON \
		  -DCMAKE_C_COMPILER=clang-9 \
		  -DCMAKE_CXX_COMPILER=clang++-9 \
		  -DLLVM_EXTERNAL_LIT=${PWD}/../llvm/build/bin/llvm-lit \
          -DCMAKE_INSTALL_PREFIX=/usr/local/polyhedral/polymer \
		  -G Ninja \
    && ninja \
    && ninja install

# == Graphite Installation ==
FROM base AS graphite-build

ARG GCC_COMMIT="0bdc158d3ee26c61b6b277238944ca5f0409e151" # snapshot of 20220819
ARG GCC_URL="https://github.com/gcc-mirror/gcc/archive/${GCC_COMMIT}.tar.gz"

RUN wget -qO- ${GCC_URL} | \
    tar xz --one-top-level=/gcc --strip-components 1 && \
    cd /gcc && \
    ./contrib/download_prerequisites && \
    ./configure \
        --prefix=/usr/local/polyhedral/graphite \
        --host=x86_64-pc-linux-gnu \
        --disable-multilib && \
    make -j32 && \
    make install && \
    ln -s /usr/local/polyhedral/graphite/bin/gcc /usr/local/bin/graphite-gcc

# Stage 3: Pluto Build
FROM base AS pluto-build

ARG PLUTO_REPO_URL="https://sourceforge.net/projects/pluto-compiler/files/pluto-0.11.4.tar.gz"
RUN wget -qO- ${PLUTO_REPO_URL} | tar xz --one-top-level=/pluto --strip-components 1 && \
    cd /pluto && \
    ./configure --prefix=/usr/local/polyhedral/pluto && \
    make -j$(nproc) && \
    sed -i -e 's#=/pluto/src/#=/usr/local/polyhedral/pluto/bin/#' polycc && \
    sed -i -e 's#=/pluto/#=/usr/local/polyhedral/pluto/bin/#' polycc && \
    make install && \
    install inscop /usr/local/polyhedral/pluto/bin/ && \
    ln -s /usr/local/polyhedral/pluto/bin/polycc /usr/local/bin/polycc

# Stage 4: ppcg Build
FROM base AS ppcg-build

ARG PPCG_REPO_URL="https://repo.or.cz/ppcg.git"
RUN git clone ${PPCG_REPO_URL} && \
    cd ppcg && \
    sed -ie 's/git:/https:/g' .gitmodules && \
    bash -ex ./get_submodules.sh && \
    bash -ex ./autogen.sh && \
    ./configure --prefix=/usr/local/polyhedral/ppcg && \
    make -j && \
    make install && \
    ln -s /usr/local/polyhedral/ppcg/bin/ppcg /usr/local/bin/ppcg

# Stage 5: pocc Build
FROM base AS pocc-build

ARG POCC_REPO_URL="https://sourceforge.net/projects/pocc/files/1.6/release/pocc-1.6.0-alpha-selfcontained.tar.gz"

RUN wget -qO- ${POCC_REPO_URL} | \
    tar xz --one-top-level=/usr/local/polyhedral/pocc --strip-components 1 && \
    cd /usr/local/polyhedral/pocc && \
    bash -x ./install.sh && \
    ln -s /usr/local/polyhedral/pocc/bin/pocc /usr/local/bin/pocc

#rose installation
FROM base AS rose-build

ARG BOOST_URL="https://archives.boost.io/release/1.82.0/source/boost_1_82_0.tar.gz"
RUN wget -qO- ${BOOST_URL} |  \
    tar xz --one-top-level=/boost --strip-components 1 && \
    cd /boost && \
    ./bootstrap.sh && \
    ./b2 --prefix=/usr/local/polyhedral/rose install

ARG ROSE_URL="https://github.com/rose-compiler/rose/archive/refs/tags/v0.11.100.0.tar.gz"

RUN wget -qO- ${ROSE_URL} | \
    tar xz --one-top-level=/rose --strip-components 1 && \
    cd /rose && \
    sed -i '1 i\#include <map>'  ./tests/smoke/unit/Sawyer/hashMapUnitTests.C && \
    ./build && \
    mkdir /rosebuild && \
    cd /rosebuild && \
    /rose/configure \
        --prefix=/usr/local/polyhedral/rose \
        --enable-languages=c,c++ \
        --with-boost=/usr/local/polyhedral/rose && \
    make -j core && \
    make install-core && \
    ln -s /usr/local/polyhedral/rose/bin/rose-compiler /usr/local/bin/rose-compiler

ARG POCC4ROSE_REPO_URL="https://sourceforge.net/projects/pocc/files/1.5/pocc-1.5.0-beta-selfcontained.tar.gz"

RUN wget -qO- ${POCC4ROSE_REPO_URL} | \
    tar xz --one-top-level=/usr/local/polyhedral/rose/pocc --strip-components 1 && \
    cd /usr/local/polyhedral/rose/pocc && \
    bash -x ./install.sh

FROM rose-build as polyopt-build

COPY polyopt_makefile.patch /rose
RUN export ROSE_ROOT=/usr/local/polyhedral/rose \
    export BOOST_ROOT=/usr/local/polyhedral/rose \
    export CXX=clang++ \
    export CC=clang && \
    cd /rose/projects/PolyOpt2 && \
    patch src/Makefile.am </rose/polyopt_makefile.patch && \
    ./bootstrap.sh && \
    ./configure \
        --prefix=/usr/local/polyhedral/polyopt \
        --with-boost=${BOOST_ROOT} \
        --with-rose=${ROSE_ROOT} \
        --with-pocc-prefix=/usr/local/polyhedral/rose/pocc \
    && \
    make -j && \
    make -j install && \
    ln -s /usr/local/polyhedral/polyopt/bin/PolyRose /usr/local/bin/polyopt

# intel compiler
FROM base AS intel-build

COPY l_BaseKit_p_2021.4.0.3422.sh .
COPY l_HPCKit_p_2021.4.0.3347.sh .
RUN bash l_BaseKit_p_2021.4.0.3422.sh -a --silent --eula accept
RUN bash l_HPCKit_p_2021.4.0.3347.sh -a --silent --eula accept

# polybench
FROM base AS polybench-build
ARG POLYBENCH_URL="https://sourceforge.net/projects/polybench/files/polybench-c-4.2.tar.gz"
RUN wget -qO- ${POLYBENCH_URL} | tar xz --one-top-level=${POLYHEDRAL_DIR} --strip-components 1

# Stage 4: Final Runtime Image
FROM ubuntu:20.04 AS runtime

# Install runtime dependencies
RUN export DEBIAN_FRONTEND=noninteractive && \
    apt-get update && apt-get install -y --no-install-recommends \
    vim binutils libc-dev libgmp10 libgcc1 libstdc++6 zlib1g libclang-cpp9 && \
    rm -rf /var/lib/apt/lists/*

# Copy build artifacts from previous stages
RUN rm -rf /usr/local

WORKDIR ${POLYHEDRAL_DIR}

COPY --from=llvm-build /usr/local /usr/local
COPY --from=graphite-build /usr/local /usr/local
COPY --from=pluto-build /usr/local /usr/local
COPY --from=ppcg-build /usr/local /usr/local
COPY --from=pocc-build /usr/local /usr/local
COPY --from=polybench-build /polyhedral /polyhedral

COPY execute_polyhedral.sh /polyhedral
COPY execute_polyhedral_syn.sh /polyhedral

COPY local.conf /etc/ld.so.conf.d/local.conf
RUN ldconfig -v

CMD ["/bin/bash"]
