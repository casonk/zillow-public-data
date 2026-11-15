#!/usr/bin/env bash
# run-job.sh — run one refresh in K3s and wait for it. This is what the host unit's ExecStart becomes in k3s mode
# (a drop-in installed by handover.sh), so the timer, the job guard, the resource arbiter, the time limit and the README
# publish step all keep working. Exit status is the job's: 0 when it succeeded, 1 otherwise.
set -euo pipefail
export KUBECONFIG="${KUBECONFIG:-$HOME/.kube/k3s.yaml}"
KUBECTL="${KUBECTL:-kubectl}"
NS=zillow-public-data
JOB="refresh-$(date +%Y%m%d-%H%M%S)"
LIMIT="${ZILLOW_JOB_LIMIT_SECONDS:-10800}"

# If systemd stops the unit (time limit, `systemctl stop`), stop the pod too instead of leaving it running.
# shellcheck disable=SC2329  # invoked by the trap below
cleanup() { "$KUBECTL" -n "$NS" delete job "$JOB" --wait=false >/dev/null 2>&1 || true; }
trap 'cleanup; exit 143' TERM INT

"$KUBECTL" -n "$NS" create job "$JOB" --from=cronjob/zillow-public-data-refresh
echo "started job $JOB"
"$KUBECTL" -n "$NS" wait --for=condition=Ready "pod" -l "job-name=$JOB" --timeout=300s >/dev/null 2>&1 || true
"$KUBECTL" -n "$NS" logs -f -l "job-name=$JOB" --tail=-1 || true

deadline=$((SECONDS + 300))
while :; do
  ok="$("$KUBECTL" -n "$NS" get job "$JOB" -o jsonpath='{.status.succeeded}' 2>/dev/null || true)"
  bad="$("$KUBECTL" -n "$NS" get job "$JOB" -o jsonpath='{.status.failed}' 2>/dev/null || true)"
  if [ "${ok:-0}" = "1" ]; then echo "job $JOB succeeded"; exit 0; fi
  if [ -n "${bad:-}" ] && [ "${bad:-0}" != "0" ]; then echo "job $JOB failed" >&2; exit 1; fi
  [ "$SECONDS" -lt "$deadline" ] || { echo "job $JOB did not finish (limit ${LIMIT}s)" >&2; cleanup; exit 1; }
  sleep 5
done
