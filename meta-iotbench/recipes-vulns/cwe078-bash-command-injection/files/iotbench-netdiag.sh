#!/bin/sh
TARGET="$1"
COMMAND="printf 'checking %s\n' $TARGET"
eval "$COMMAND"
