# HotSpot client is unavailable on aarch64; Zero covers targets without a JIT.
JVM_VARIANT = "server"
JVM_VARIANT:mips = "zero"
JVM_VARIANT:mipsel = "zero"

