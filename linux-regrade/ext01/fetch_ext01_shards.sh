#!/usr/bin/env bash
# EXT-01 stage 2b: progress or results for every shard that is still recorded in this folder.
HERE="$(cd "$(dirname "$0")" && pwd)"
for s in A B C; do echo; echo "######## shard $s"; SHARD=$s bash "$HERE/fetch_ext01_to_mac.sh"; done
