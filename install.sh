#!/bin/bash

TAR_FILE="TUXIXI-Terminal-v1.1.2.tar.gz"

if [ ! -f "$TAR_FILE" ]; then
    echo "Error: File not found!"
    exit 1
fi

tar -xzf "$TAR_FILE"
chmod -R +x .

echo "ready tuxixi"
