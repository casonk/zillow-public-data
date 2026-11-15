#!/usr/bin/env bash
# verify.sh — prove the refresh's network policy and mounts from inside a pod that carries its labels.
# Every probe states what it expects; one that cannot run is a FAIL, never an "ok".
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export KUBECONFIG="${KUBECONFIG:-$HOME/.kube/k3s.yaml}"
NS=zillow-public-data POD=zillow-public-data-verify
fail=0
# shellcheck disable=SC2329  # invoked by the EXIT trap below
cleanup() { kubectl -n "$NS" delete pod "$POD" --ignore-not-found --wait=false >/dev/null 2>&1; }
trap cleanup EXIT
# A previous run's pod may still be terminating (its `sleep` ignores SIGTERM); wait until it is gone.
kubectl -n "$NS" delete pod "$POD" --ignore-not-found --wait=true --timeout=120s >/dev/null 2>&1 || true

kubectl apply -f "$HERE/manifests/verify-pod.yaml" >/dev/null
if ! kubectl -n "$NS" wait --for=condition=Ready "pod/$POD" --timeout=120s >/dev/null 2>&1; then
  echo "FAIL  the verification pod did not become ready; nothing was verified"
  kubectl -n "$NS" describe pod "$POD" 2>&1 | tail -8
  exit 2
fi

probe() { # probe <expect: open|closed> <label> <host> <port>
  local expect=$1 label=$2 host=$3 port=$4 got
  got="$(kubectl -n "$NS" exec "$POD" -- python3 -c "
import socket,sys
try:
    socket.create_connection(('$host', $port), timeout=5).close(); print('open')
except OSError:
    print('closed')" 2>/dev/null | tail -1)"
  case "$got" in
    open|closed)
      if [ "$got" = "$expect" ]; then echo "ok    $label ($host:$port is $got)"
      else echo "FAIL  $label ($host:$port is $got, expected $expect)"; fail=1; fi ;;
    *) echo "FAIL  $label (could not run the probe inside the pod)"; fail=1 ;;
  esac
}
probe open   "Zillow public files"       files.zillowstatic.com 443
probe closed "other port on Zillow"      files.zillowstatic.com 80
probe closed "Zillow website"            www.zillow.com 443
probe closed "arbitrary internet host"   example.com 443
probe closed "link-local metadata"       169.254.169.254 80
probe closed "Kubernetes API"            kubernetes.default.svc 443
NODE_IP="$(kubectl get node -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}' | awk '{print $1}')"
probe closed "host SSH (node address)"   "$NODE_IP" 22
probe closed "in-cluster registry"       10.43.0.50 5000

check() { # check <label> <command run in the pod>
  if kubectl -n "$NS" exec "$POD" -- sh -c "$2" >/dev/null 2>&1; then echo "ok    $1"
  else echo "FAIL  $1"; fail=1; fi
}
echo "--- mounts and identity:"
check "no service-account token mounted"   'test ! -e /var/run/secrets/kubernetes.io'
check "data is writable"                   'touch /app/data/.write-probe && rm /app/data/.write-probe'
check "viz is writable"                    'touch /app/viz/.write-probe && rm /app/viz/.write-probe'
check "root filesystem is read-only"       '! touch /app/.write-probe'
check "the dataset catalog is present"     'test -s /app/doc_urls.pickle'
check "the libraries import"               'python3 -c "import pandas, requests, matplotlib"'
exit $fail
