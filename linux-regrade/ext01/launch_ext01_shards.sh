#!/usr/bin/env bash
# EXT-01 stage 2b: start the three shards one after another (about 5 minutes each).
#   COMMIT=<sha> bash launch_ext01_shards.sh
# Then later:  bash fetch_ext01_shards.sh
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
: "${COMMIT:?set COMMIT}"
export COMMIT STAGE2=ext01_stage2b.sh TYPE=m5.2xlarge
SHARD=A SHARD_ENTRIES="4 5" REP_EXTRA=""                                          bash "$HERE/launch_ext01_from_mac.sh" || echo "!! shard A failed to start"
SHARD=B SHARD_ENTRIES="6 7" REP_EXTRA=""                                          bash "$HERE/launch_ext01_from_mac.sh" || echo "!! shard B failed to start"
SHARD=C SHARD_ENTRIES="2"   REP_EXTRA="1:django__django-12856 3:pallets__flask-4045" bash "$HERE/launch_ext01_from_mac.sh" || echo "!! shard C failed to start"
echo; echo "All shards started (see any '!!' lines above). Fetch later with: bash $HERE/fetch_ext01_shards.sh"
