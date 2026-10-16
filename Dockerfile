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

# /cache and /workdir are volumes: Docker copies this ownership into them when
# they are created empty.
RUN useradd -m -u 1000 -s /bin/bash yocto && \
    mkdir -p /opt/yocto/layers /cache /workdir && \
    chown -R yocto:yocto /opt/yocto /cache /workdir

USER yocto
WORKDIR /opt/yocto/layers

# Only pinned layers live in the image: no firmware layer and no build output,
# so the image stays small and can be pushed to a registry.
# meta-oe provides the PHP recipe and is pinned to the revision used with 6.0.3.
ARG YOCTO_RELEASE=yocto-6.0.3
ARG META_OPENEMBEDDED_REV=14282a02be9c74a1276a7cda7d6c89e054699a11
RUN git clone --depth 1 -b "${YOCTO_RELEASE}" https://git.openembedded.org/bitbake && \
    git clone --depth 1 -b "${YOCTO_RELEASE}" https://git.openembedded.org/openembedded-core && \
    git clone --depth 1 -b "${YOCTO_RELEASE}" https://git.yoctoproject.org/meta-yocto && \
    git clone --single-branch -b wrynose https://git.openembedded.org/meta-openembedded && \
    git -C meta-openembedded checkout "${META_OPENEMBEDDED_REV}"

# Java firmware fixtures use the cross-built runtime and native bootstrap JDK.
ARG META_OPENJDK_REV=0fefb16cf99e687a53ae5e36a163af962dd64e9f
RUN git clone --single-branch -b wrynose https://github.com/amarula/meta-openjdk.git && \
    git -C meta-openjdk checkout "${META_OPENJDK_REV}"

COPY --chown=yocto:yocto builder/ /opt/yocto/

WORKDIR /workdir

CMD ["/bin/bash"]
