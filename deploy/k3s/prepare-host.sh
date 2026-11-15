#!/usr/bin/env bash
# prepare-host.sh — label the data and viz folders so containers may use them. No sudo.
# SELinux keeps containers out of ordinary home-directory files; container_file_t opens exactly these two
# folders. Host programs (the publish step, your notebooks) read them as before.
# Undo with:  restorecon -RF <the two folders>   (printed below)
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
DATA_DIR="${ZILLOW_DATA_DIR:-$REPO/data}"
VIZ_DIR="${ZILLOW_VIZ_DIR:-$REPO/viz}"
for d in "$DATA_DIR" "$VIZ_DIR"; do
  mkdir -p "$d"
  chcon -R -t container_file_t "$d"
  echo "labelled $d: $(ls -Zd "$d" | awk '{print $1}')"
done
echo "Undo with: restorecon -RF '$DATA_DIR' '$VIZ_DIR'"
echo "A system-wide relabel (restorecon or an OS upgrade) would reset these; re-run this script if the pod loses access."
