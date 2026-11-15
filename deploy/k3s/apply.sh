#!/usr/bin/env bash
# apply.sh — create the Zillow refresh template in K3s. No sudo. Safe to repeat.
# The namespace, volumes and network policy exist before the CronJob, which is only a template for run-job.sh and
# stays suspended. First time on this machine: prepare-host.sh and build-image.sh come first.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
export KUBECONFIG="${KUBECONFIG:-$HOME/.kube/k3s.yaml}"
DATA_DIR="${ZILLOW_DATA_DIR:-$REPO/data}"
VIZ_DIR="${ZILLOW_VIZ_DIR:-$REPO/viz}"

kubectl wait --for=condition=Ready node --all --timeout=60s
kubectl get crd ciliumnetworkpolicies.cilium.io >/dev/null
for d in "$DATA_DIR" "$VIZ_DIR"; do
  [ -d "$d" ] || { echo "missing $d; run deploy/k3s/prepare-host.sh first"; exit 1; }
  ctx="$(stat -c %C "$d")"
  case "$ctx" in *container_file_t*) ;; *) echo "$d is labelled $ctx; run deploy/k3s/prepare-host.sh first"; exit 1 ;; esac
done
NODE="$(kubectl get node -o jsonpath='{.items[0].metadata.name}')"

kubectl apply -f "$HERE/manifests/00-namespace.yaml"
sed -e "s#__DATA_DIR__#$DATA_DIR#g" -e "s#__VIZ_DIR__#$VIZ_DIR#g" -e "s#__NODE__#$NODE#g" \
  "$HERE/manifests/10-volumes.yaml.tmpl" | kubectl apply -f -
kubectl apply -f "$HERE/manifests/30-network-policy.yaml"
kubectl apply -f "$HERE/manifests/20-cronjob.yaml"
echo "Deployed (the CronJob is a suspended template). Prove it with deploy/k3s/verify.sh, then switch the unit over with deploy/deploy.sh --mode k3s up"
