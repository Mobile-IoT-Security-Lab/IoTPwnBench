SUMMARY = "IoTBench opt-in fixture - CWE-502 Java deserialization"
DESCRIPTION = "One missing type restriction, CWE-20 contributing. Harmless in-memory callback marker. Disposable isolated tests only."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=2ac030fbcf0423505c28549799c198f7"
FILESEXTRAPATHS:prepend := "${THISDIR}/files:${THISDIR}/../../../scripts:"
SRC_URI = "file://LICENSE file://NOTICE file://FixtureData.java file://FixtureMarker.java file://FixtureDeserialize.java file://FixtureHarness.java file://fixture-build.py file://vectors.json file://ground-truth.json file://test-java-deserialization-fixture.py file://test-java-command-fixture.py"
S = "${UNPACKDIR}"
DEPENDS = "openjdk-bin-native"
RDEPENDS:${PN} = "openjdk busybox util-linux-unshare util-linux-setpriv python3-modules ldd"
inherit useradd
USERADD_PACKAGES = "${PN}"
GROUPADD_PARAM:${PN} = "--system --gid 992 javadeserialize"
USERADD_PARAM:${PN} = "--system --uid 992 --gid javadeserialize --home-dir /nonexistent --no-create-home --shell /sbin/nologin javadeserialize"
IOTBENCH_BUILD_MODE ?= "production"
IOTBENCH_ENABLE_JAVA_DESERIALIZATION_FIXTURE ?= "0"

python __anonymous() {
    if (d.getVar('IOTBENCH_BUILD_MODE') != 'fixture' or
            d.getVar('IOTBENCH_ENABLE_JAVA_DESERIALIZATION_FIXTURE') != '1'):
        raise bb.parse.SkipRecipe('Java deserialization requires explicit opt-in and fixture mode')
}

do_compile[vardeps] += "IOTBENCH_BUILD_MODE IOTBENCH_ENABLE_JAVA_DESERIALIZATION_FIXTURE"
do_compile() {
    ${PYTHON} ${S}/fixture-build.py --fixture-build --with-tests \
        --source ${S} --output ${B}/jars --javac ${STAGING_LIBDIR_NATIVE}/jvm/bin/javac
}

do_install() {
    install -d ${D}${datadir}/iotbench/java-deserialization-fixture
    install -m 0644 ${B}/jars/*.jar ${D}${datadir}/iotbench/java-deserialization-fixture/
    for fixture_file in LICENSE NOTICE FixtureData.java FixtureMarker.java FixtureDeserialize.java FixtureHarness.java vectors.json ground-truth.json test-java-deserialization-fixture.py test-java-command-fixture.py; do
        install -m 0644 ${S}/$fixture_file ${D}${datadir}/iotbench/java-deserialization-fixture/
    done
}

FILES:${PN} = "${datadir}/iotbench/java-deserialization-fixture"
