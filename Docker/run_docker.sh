#!/bin/bash
set -e

BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
WORK_DIR="$BASE_DIR/workdir"

mkdir -p "$WORK_DIR"

docker pull tuoli96/hanguang:v1

docker run -it --rm \
    -e HOST_UID="$(id -u)" \
    -e HOST_GID="$(id -g)" \
	-e DS_API_KEY \
    -v "$WORK_DIR:/workdir" \
	--network host \
    --name hanguang \
    hanguang:v1
