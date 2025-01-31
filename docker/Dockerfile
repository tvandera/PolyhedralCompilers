# Base Stage: Common build environment
FROM ubuntu:20.04 AS base

ARG DEBIAN_FRONTEND=noninteractive
ENV POLYHEDRAL_DIR="/usr/local/lib/polyhedral"

# Set ARGs for user ID and GID (optional)
ARG GID
ARG UID
RUN echo "Group ID: $GID"
RUN echo "User ID: $UID"

# Install essential build tools and dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libtool autoconf automake libltdl-dev pkg-config flex bison libgmp-dev \
    clang-9 libclang-9-dev llvm-9 llvm-9-tools llvm-9-dev texinfo vim ninja-build git \
    libxml2-dev ccache ghostscript \
    wget curl rsync \
    python3 python3-dev python3-pip \
    libhdf5-dev  libjpeg-dev zlib1g-dev && \
    ln -sf /usr/bin/python3 /usr/bin/python && \
    rm -rf /var/lib/apt/lists/*


# Install Python packages
RUN pip3 install --upgrade pip && pip install --no-cache-dir \
    matplotlib numpy pandas scipy tables pybind11>=2.8.0 PyYAML dataclasses

ARG CMAKE_FILE="https://github.com/Kitware/CMake/releases/download/v3.23.2/cmake-3.23.2-linux-x86_64.tar.gz"
RUN wget -qO- ${CMAKE_FILE} | tar xz --one-top-level=/usr/local --strip-components 1

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
        -DLLVM_CCACHE_BUILD=True \
        -DLLVM_USE_LINKER=gold && \
    ninja all && \
    ninja install

# Stage 3: Pluto Build
FROM base AS pluto-build

ARG PLUTO_REPO_URL="https://sourceforge.net/projects/pluto-compiler/files/pluto-0.11.4.tar.gz"
RUN wget -qO- ${PLUTO_REPO_URL} | tar xz --one-top-level=/pluto --strip-components 1 && \
    cd /pluto && \
    ./configure --disable-static && \
    make -j$(nproc) && \
    make install && \
    ldconfig

# Stage 4: ppcg Build
FROM base AS ppcg-build

ARG PPCG_REPO_URL="https://repo.or.cz/ppcg.git"
RUN git clone ${PPCG_REPO_URL} && \
    cd ppcg && \
    sed -ie 's/git:/https:/g' .gitmodules && \
    bash -ex ./get_submodules.sh && \
    bash -ex ./autogen.sh && \
    ./configure && \
    make -j && \
    make install

# Stage 5: pocc Build
FROM base AS pocc-build

ARG POCC_REPO_URL="https://sourceforge.net/projects/pocc/files/1.6/release/pocc-1.6.0-alpha-selfcontained.tar.gz"
RUN wget -qO- ${POCC_REPO_URL} | \
    tar xz --one-top-level=/pocc --strip-components 1 && \
    cd /pocc && \
    bash -x ./install.sh && \
    make install


# == Graphite Installation ==
FROM base AS graphite-build

ARG GCC_COMMIT="0bdc158d3ee26c61b6b277238944ca5f0409e151" # snapshot of 20220819
ARG GCC_URL="https://github.com/gcc-mirror/gcc/archive/${GCC_COMMIT}.tar.gz"

RUN wget -qO- ${GCC_URL} | \
    tar xz --one-top-level=/gcc --strip-components 1 && \
    cd /gcc && \
    ./contrib/download_prerequisites && \
    ./configure --host=x86_64-pc-linux-gnu --disable-multilib && \
    make -j32 && \
    make install

#rose installation
FROM base AS rose-build

ARG BOOST_URL="https://archives.boost.io/release/1.82.0/source/boost_1_82_0.tar.gz"
RUN wget -qO- ${BOOST_URL} |  \
    tar xz --one-top-level=/boost --strip-components 1 && \
    cd /boost && \
    ./bootstrap.sh && \
    ./b2 --prefix=/boost/install link=static install

ARG ROSE_URL="https://github.com/rose-compiler/rose/archive/refs/tags/v0.11.100.0.tar.gz"

RUN wget -qO- ${ROSE_URL} | \
    tar xz --one-top-level=/rose --strip-components 1 && \
    cd /rose && \
    sed -i '1 i\#include <map>'  ./tests/smoke/unit/Sawyer/hashMapUnitTests.C && \
    ./build && \
    mkdir /rosebuild && \
    cd /rosebuild && \
    /rose/configure \
        --prefix=/usr/local \
        --disable-shared \
        --enable-languages=c,c++ \
        --with-boost=/boost/install && \
    make -j core && \
    make install-core

RUN export ROSE_ROOT=/usr/local && \
    export BOOST_ROOT="/boost/install" && \
    cd /rose/projects/PolyOpt2 && \
    ./install.sh && \
    make -j install

# intel compiler
FROM base AS intel-build

COPY l_BaseKit_p_2021.4.0.3422.sh .
COPY l_HPCKit_p_2021.4.0.3347.sh .
RUN bash l_BaseKit_p_2021.4.0.3422.sh -a --silent --eula accept
RUN bash l_HPCKit_p_2021.4.0.3347.sh -a --silent --eula accept

# Stage 4: Final Runtime Image
FROM ubuntu:20.04 AS runtime
ARG DEBIAN_FRONTEND=noninteractive
ENV POLYHEDRAL_DIR="/polyhedral"

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgmp10 libgcc1 libstdc++6 zlib1g && \
    rm -rf /var/lib/apt/lists/*

# Copy build artifacts from previous stages
# COPY --from=llvm-build /usr/local /usr/local
# COPY --from=pluto-build /usr/local /usr/local

WORKDIR ${POLYHEDRAL_DIR}
COPY execute_polyhedral.sh .
COPY execute_polyhedral_syn.sh .

CMD ["/bin/bash"]

