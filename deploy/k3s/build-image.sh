#!/usr/bin/env bash
# build-image.sh — build the image and push it to the in-cluster registry (no sudo).
# Needs crew-chief's deploy/k3s/install-registry.sh once, and enable-registry-mirror.sh once as root.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
# crew-chief holds the registry push helper. It sits next to a util-repos repository and one level over from the
# other categories (research-repos/, doc-repos/, ...); CREW_CHIEF_DIR overrides both.
CREW_CHIEF="${CREW_CHIEF_DIR:-}"
if [ -z "$CREW_CHIEF" ]; then
  for candidate in "$REPO/../crew-chief" "$REPO/../../util-repos/crew-chief"; do
    [ -x "$candidate/deploy/k3s/push-image.sh" ] && { CREW_CHIEF="$candidate"; break; }
  done
fi
[ -x "$CREW_CHIEF/deploy/k3s/push-image.sh" ] || { echo "cannot find crew-chief's push-image.sh; set CREW_CHIEF_DIR" >&2; exit 1; }
IMAGE="localhost/zillow-public-data:k3s"
SOURCES=(refresh.py doc_urls.pickle requirements.txt)
WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT
# The pod runs what is committed; the host runs whatever is in the checkout. If they differ, the two behave
# differently (this once made two writers disagree about a file's format). Build only from committed code, or
# say so explicitly.
if [ -z "${ALLOW_DIRTY:-}" ] && [ -n "$(git -C "$REPO" status --porcelain -- "${SOURCES[@]}")" ]; then
  echo "${SOURCES[*]} has uncommitted changes; the image would not match what is committed. Commit them, or set ALLOW_DIRTY=1." >&2
  exit 1
fi
for source in "${SOURCES[@]}"; do
  mkdir -p "$WORK/$(dirname "$source")"
  cp -r "$REPO/$source" "$WORK/$source"
done
find "$WORK" \( -name '__pycache__' -o -name '*.pyc' -o -name '*.egg-info' \) -prune -exec rm -rf {} +
cp "$HERE/Containerfile" "$WORK/Containerfile"
podman build -t "$IMAGE" -f "$WORK/Containerfile" "$WORK"
"$CREW_CHIEF/deploy/k3s/push-image.sh" "$IMAGE" zillow-public-data:k3s
echo "Next: deploy/k3s/apply.sh"
