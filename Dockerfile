FROM debian:12

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    build-essential \
    chrpath \
    cpio \
    nano \
    vim \
    debianutils \
    diffstat \
    file \
    gawk \
    gcc \
    git \
    iputils-ping \
    libacl1 \
    libcrypt-dev \
    locales \
    python3 \
    python3-git \
    python3-jinja2 \
    python3-pexpect \
    python3-pip \
    python3-subunit \
    socat \
    texinfo \
    unzip \
    wget \
    xz-utils \
    zstd \
    && rm -rf /var/lib/apt/lists/*

RUN sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen && \
    locale-gen

ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8

RUN useradd -m -u 1000 -s /bin/bash yocto

WORKDIR /workdir

RUN mkdir -p /workdir/yocto-firmware/layers && \
    chown -R yocto:yocto /workdir

WORKDIR /workdir/yocto-firmware

USER yocto

RUN git clone -b yocto-6.0.3 \
    https://git.openembedded.org/bitbake \
    layers/bitbake

RUN git clone -b yocto-6.0.3 \
    https://git.openembedded.org/openembedded-core \
    layers/openembedded-core

RUN git clone -b yocto-6.0.3 \
    https://git.yoctoproject.org/meta-yocto \
    layers/meta-yocto

RUN mkdir build

RUN bash -lc "source layers/openembedded-core/oe-init-build-env build"


CMD ["/bin/bash"]
