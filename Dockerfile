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

# meta-oe contains the PHP recipe. Pin the revision used with Yocto 6.0.3 so
# rebuilding the builder image remains deterministic.
ARG META_OPENEMBEDDED_REV=14282a02be9c74a1276a7cda7d6c89e054699a11
RUN git clone -b wrynose \
    https://git.openembedded.org/meta-openembedded \
    layers/meta-openembedded && \
    git -C layers/meta-openembedded checkout "${META_OPENEMBEDDED_REV}"

COPY --chown=yocto:yocto meta-router-dashboard layers/meta-router-dashboard

RUN mkdir build

ARG YOCTO_MACHINE=qemuarm64
RUN case "${YOCTO_MACHINE}" in \
        ''|*[!A-Za-z0-9._+-]*) echo "YOCTO_MACHINE non valido: ${YOCTO_MACHINE}" >&2; exit 1 ;; \
    esac && \
    bash -lc "source layers/openembedded-core/oe-init-build-env build && \
    sed -i '/^[[:space:]]*MACHINE[[:space:]]*=/d' conf/local.conf && \
    printf '\nMACHINE = \"${YOCTO_MACHINE}\"\n' >> conf/local.conf && \
    bitbake core-image-minimal && \
    bitbake-layers add-layer ../layers/meta-openembedded/meta-oe && \
    bitbake-layers add-layer ../layers/meta-router-dashboard"


CMD ["/bin/bash"]
