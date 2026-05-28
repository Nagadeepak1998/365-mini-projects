#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <seconds>"
  exit 1
fi

if ! [[ "$1" =~ ^[0-9]+$ ]]; then
  echo "Error: seconds must be a non-negative integer"
  exit 1
fi

seconds=$1
days=$((seconds / 86400))
seconds=$((seconds % 86400))
hours=$((seconds / 3600))
seconds=$((seconds % 3600))
minutes=$((seconds / 60))
seconds=$((seconds % 60))

printf "%dd %02dh %02dm %02ds\n" "$days" "$hours" "$minutes" "$seconds"
