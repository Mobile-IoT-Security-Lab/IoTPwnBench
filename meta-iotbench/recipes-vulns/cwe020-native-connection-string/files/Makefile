# Native Linux build. Default output excludes the fixture and SQLite entirely.
CC ?= cc
BUILD_DIR ?= build
IOTBENCH_BUILD_MODE ?= production
IOTBENCH_ENABLE_CONNECTION_FIXTURE ?= 0
CFLAGS ?= -O2 -g
COMMON = -std=c99 -Wall -Wextra -Werror -D_FORTIFY_SOURCE=2 -fstack-protector-strong -fPIE
LINK_HARDEN = -pie -Wl,-z,relro,-z,now,-z,noexecstack
SOURCE = $(dir $(abspath $(lastword $(MAKEFILE_LIST))))fixture-connection.c
ENABLED = -DIOTBENCH_CONNECTION_FIXTURE_ENABLED=1
SANITIZE = -fsanitize=address,undefined -fno-sanitize-recover=all -fno-omit-frame-pointer

.PHONY: all production fixture sanitize check-fixture
all: production

production:
	mkdir -p "$(BUILD_DIR)"
	$(CC) $(CPPFLAGS) $(CFLAGS) $(COMMON) "$(SOURCE)" $(LDFLAGS) $(LINK_HARDEN) -o "$(BUILD_DIR)/fixture-connection-disabled"

check-fixture:
	@test "$(IOTBENCH_BUILD_MODE)" = fixture && test "$(IOTBENCH_ENABLE_CONNECTION_FIXTURE)" = 1 || { echo 'Requires IOTBENCH_BUILD_MODE=fixture and IOTBENCH_ENABLE_CONNECTION_FIXTURE=1' >&2; exit 1; }

fixture: check-fixture
	mkdir -p "$(BUILD_DIR)"
	$(CC) $(CPPFLAGS) $(CFLAGS) $(COMMON) $(ENABLED) "$(SOURCE)" $(LDFLAGS) $(LINK_HARDEN) -lsqlite3 -o "$(BUILD_DIR)/fixture-connection"

sanitize: check-fixture
	mkdir -p "$(BUILD_DIR)"
	$(CC) $(CPPFLAGS) $(CFLAGS) $(COMMON) $(ENABLED) $(SANITIZE) "$(SOURCE)" $(LDFLAGS) $(LINK_HARDEN) -lsqlite3 -o "$(BUILD_DIR)/fixture-connection-sanitize"
