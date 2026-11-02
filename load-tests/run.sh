#!/usr/bin/env bash
# Run a Drive load-test scenario in CLI mode.
#
# Usage:
#   ./run.sh [scenario.jmx] [jmeter options]
#
# The first argument may name a scenario file (default: drive-session.jmx).
#
# Examples:
#   ./run.sh -JUSERS=100 -JRAMP_UP=60 -JDURATION=600
#   ./run.sh drive-session-read-heavy.jmx -JUSERS=100 -JRAMP_UP=60 -JDURATION=600
#   ./run.sh -JBASE_URL=https://drive-load.example.com -JUSERS=500 -JRAMP_UP=300 -JDURATION=1800
#
# Every -J property is optional, see README.md for the full list and defaults.
set -euo pipefail
cd "$(dirname "$0")"

SCENARIO="drive-session.jmx"
if [ $# -ge 1 ] && [[ "$1" == *.jmx ]]; then
  SCENARIO="$1"
  shift
fi
if [ ! -f "$SCENARIO" ]; then
  echo "Scenario file not found: $SCENARIO" >&2
  exit 1
fi

mkdir -p results

EXTRA_ARGS=()
# Per-injector properties (USER_OFFSET notably), see user.properties.example.
if [ -f user.properties ]; then
  EXTRA_ARGS+=(-q user.properties)
fi

TS=$(date +%Y%m%d-%H%M%S)
RUN="results/$(basename "$SCENARIO" .jmx)-$TS"

jmeter -n -t "$SCENARIO" \
  -l "$RUN.jtl" \
  -j "$RUN.log" \
  -e -o "$RUN-report" \
  "${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"}" \
  "$@"

echo
echo "Raw results:    $RUN.jtl"
echo "JMeter log:     $RUN.log"
echo "HTML dashboard: $RUN-report/index.html"
