DESCRIPTION = "Opt-in synthetic Java command injection; one incomplete label check per JAR. Disposable isolated tests only."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=2ac030fbcf0423505c28549799c198f7"
FILESEXTRAPATHS:prepend := "${THISDIR}/files:${THISDIR}/../../../scripts:"
SRC_URI = "file://LICENSE file://NOTICE file://FixtureRequest.java file://FixtureOsCommand.java file://FixtureAppCommand.java file://fixture-build.py file://requests.json file://ground-truth.json file://test-java-command-fixture.py"
S = "${UNPACKDIR}"
DEPENDS = "openjdk-bin-native"
RDEPENDS:${PN} = "openjdk busybox util-linux-unshare util-linux-setpriv python3-modules ldd"
inherit useradd
USERADD_PACKAGES = "${PN}"
GROUPADD_PARAM:${PN} = "--system --gid 991 javacommand"
USERADD_PARAM:${PN} = "--system --uid 991 --gid javacommand --home-dir /nonexistent --no-create-home --shell /sbin/nologin javacommand"
IOTBENCH_BUILD_MODE ?= "production"
IOTBENCH_ENABLE_JAVA_COMMAND_FIXTURE ?= "0"

python __anonymous() {
    if (d.getVar('IOTBENCH_BUILD_MODE') != 'fixture' or
            d.getVar('IOTBENCH_ENABLE_JAVA_COMMAND_FIXTURE') != '1'):
        raise bb.parse.SkipRecipe('Java command fixture requires explicit opt-in and fixture mode')
}

do_compile[vardeps] += "IOTBENCH_BUILD_MODE IOTBENCH_ENABLE_JAVA_COMMAND_FIXTURE"
do_compile() {
    ${PYTHON} ${S}/fixture-build.py --fixture-build --variant ${JAVA_COMMAND_VARIANT} \
        --source ${S} --output ${B}/jars --javac ${STAGING_LIBDIR_NATIVE}/jvm/bin/javac
}

do_install() {
    install -d ${D}${datadir}/iotbench/java-command-fixture
    install -m 0644 ${B}/jars/fixture-${JAVA_COMMAND_VARIANT}-command.jar \
        ${D}${datadir}/iotbench/java-command-fixture/
    for fixture_file in LICENSE NOTICE FixtureRequest.java ${JAVA_COMMAND_MAIN}.java requests.json ground-truth.json test-java-command-fixture.py; do
        install -m 0644 ${S}/$fixture_file ${D}${datadir}/iotbench/java-command-fixture/
    done
}

FILES:${PN} = "${datadir}/iotbench/java-command-fixture"
