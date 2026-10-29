# Offline native build. Default target contains only the disabled stub.
CC ?= cc
BUILD_DIR ?= build
IOTBENCH_BUILD_MODE ?= production
IOTBENCH_ENABLE_NATIVE_BUFFER_FIXTURE ?= 0
CFLAGS ?= -O2 -g
HARDEN = -D_FORTIFY_SOURCE=2 -fstack-protector-strong -fPIE
LINK_HARDEN = -pie -Wl,-z,relro,-z,now,-z,noexecstack
COMMON = -std=c99 -Wall -Wextra -Werror
FIXTURE = -DIOTBENCH_BUFFER_FIXTURE_ENABLED=1 -O1 -g -fno-inline -fno-lto
ASAN = -fsanitize=address -fno-sanitize-recover=all -fno-omit-frame-pointer
SOURCE = $(dir $(abspath $(lastword $(MAKEFILE_LIST))))fixture-buffer-write.c

.PHONY: all production fixture asan check-fixture
all: production

production:
	mkdir -p "$(BUILD_DIR)"
	$(CC) $(CPPFLAGS) $(CFLAGS) $(COMMON) $(HARDEN) "$(SOURCE)" $(LDFLAGS) $(LINK_HARDEN) -o "$(BUILD_DIR)/fixture-buffer-write-disabled"

check-fixture:
	@test "$(IOTBENCH_BUILD_MODE)" = fixture && test "$(IOTBENCH_ENABLE_NATIVE_BUFFER_FIXTURE)" = 1 || { echo 'Requires IOTBENCH_BUILD_MODE=fixture and IOTBENCH_ENABLE_NATIVE_BUFFER_FIXTURE=1' >&2; exit 1; }

fixture: check-fixture
	mkdir -p "$(BUILD_DIR)"
	$(CC) $(CPPFLAGS) $(CFLAGS) $(COMMON) $(HARDEN) $(FIXTURE) "$(SOURCE)" $(LDFLAGS) $(LINK_HARDEN) -o "$(BUILD_DIR)/fixture-buffer-write"

asan: check-fixture
	mkdir -p "$(BUILD_DIR)"
	$(CC) $(CPPFLAGS) $(CFLAGS) $(COMMON) $(HARDEN) $(FIXTURE) $(ASAN) "$(SOURCE)" $(LDFLAGS) $(LINK_HARDEN) -o "$(BUILD_DIR)/fixture-buffer-write-asan"
