#!/usr/bin/env bash
# deploy.sh — Weekly Zillow public-data download and plots One entry point, one setting.
#
#   deploy/deploy.sh [--mode dev|host|k3s] up|down|status|verify|mode
#
# The mode comes from, first match wins:
#   1. --mode on the command line
#   2. ZILLOW_DEPLOY_MODE in the environment
#   3. ZILLOW_DEPLOY_MODE in config/deploy.local.env (copy config/deploy.example.env; never committed)
#   4. dev
#
# Only k3s mode touches kubectl, podman or a cluster. See docs/deployment.md.
# -E: the ERR trap used by `k3s up` must also fire for failures inside functions.
set -eEuo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
K3S_DIR="${ZILLOW_K3S_DIR:-$HERE/k3s}"
CONFIG_FILE="${ZILLOW_DEPLOY_CONFIG:-$REPO/config/deploy.local.env}"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/zillow-public-data"
MARKER="$STATE_DIR/deploy-mode"
MODES="dev host k3s"
TIMER="zillow-public-data-refresh.timer"
NAMESPACE="zillow-public-data"

usage() {
  sed -n '2,12p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
  exit "${1:-2}"
}

mode="" source_of=""
cmd=""
while [ $# -gt 0 ]; do
  case "$1" in
    --mode) mode="${2:?--mode needs dev, host or k3s}"; source_of="--mode"; shift 2 ;;
    --mode=*) mode="${1#--mode=}"; source_of="--mode"; shift ;;
    -h|--help) usage 0 ;;
    up|down|status|verify|mode) cmd="$1"; shift ;;
    *) echo "unknown argument: $1" >&2; usage 2 ;;
  esac
done
[ -n "$cmd" ] || usage 2

if [ -z "$mode" ] && [ -n "${ZILLOW_DEPLOY_MODE:-}" ]; then mode="$ZILLOW_DEPLOY_MODE"; source_of="environment"; fi
if [ -z "$mode" ] && [ -f "$CONFIG_FILE" ]; then
  # No `|| true`: if reading the config fails, say so rather than quietly choosing dev.
  line="$(python3 -I "$K3S_DIR/env_value.py" "$CONFIG_FILE" ZILLOW_DEPLOY_MODE)"
  if [ -n "$line" ]; then mode="${line#ZILLOW_DEPLOY_MODE=}"; source_of="$CONFIG_FILE"; fi
fi
if [ -z "$mode" ]; then mode="dev"; source_of="default"; fi
case " $MODES " in *" $mode "*) ;; *) echo "unknown deployment mode '$mode' (from $source_of); use one of: $MODES" >&2; exit 2 ;; esac

need() { command -v "$1" >/dev/null 2>&1 || { echo "$2" >&2; exit 1; }; }
marker_is_k3s() { [ -f "$MARKER" ] && [ "$(cat "$MARKER")" = k3s ]; }
set_marker() { mkdir -p "$STATE_DIR"; echo "$1" > "$MARKER"; }
clear_marker() { rm -f "$MARKER"; }
kc() { KUBECONFIG="${KUBECONFIG:-$HOME/.kube/k3s.yaml}" "${KUBECTL:-kubectl}" "$@"; }
registry_ready() { curl -fsS --max-time 5 http://10.43.0.50:5000/v2/ >/dev/null 2>&1; }
require_cluster_tools() {
  need "${KUBECTL:-kubectl}" "k3s mode needs kubectl and a running K3s (see docs/deployment.md). dev and host modes need neither."
  need podman "k3s mode needs podman, to build the image"
  export KUBECONFIG="${KUBECONFIG:-$HOME/.kube/k3s.yaml}"
  registry_ready || {
    echo "k3s mode needs the in-cluster registry: run install-registry.sh and enable-registry-mirror.sh from crew-chief's deploy/k3s" >&2
    exit 1
  }
}

timer_installed() { systemctl --user cat "$TIMER" >/dev/null 2>&1; }
show_timer() {
  printf '%-34s %-9s %s\n' "$TIMER" "$(systemctl --user is-active "$TIMER" 2>/dev/null || true)" \
    "$(systemctl --user is-enabled "$TIMER" 2>/dev/null || true)"
}

case "$cmd:$mode" in
  mode:*) echo "$mode (from $source_of)" ;;

  # ---- dev: one run in the foreground, no systemd, no cluster ----
  up:dev) python3 refresh.py --resume ;;
  down:dev) echo "dev mode runs once in the foreground; there is nothing to stop" ;;
  status:dev|verify:dev) echo dev mode runs once in the foreground ;;

  # ---- host: the systemd user timer ----
  up:host)
    if marker_is_k3s; then
      echo "the K3s run is active; switching the unit back to run on the host"
      if command -v "${KUBECTL:-kubectl}" >/dev/null 2>&1; then "$K3S_DIR/handover.sh" pod-off
      else echo "kubectl is not installed: suspend the CronJob yourself (docs/deployment.md) or both will run" >&2; exit 1; fi
    fi
    timer_installed || {
      echo "$TIMER is not installed. Install it with Clockwork from its manifest (see docs/deployment.md)" >&2
      exit 1
    }
    systemctl --user enable --now "$TIMER"
    clear_marker
    ;;
  down:host) systemctl --user disable --now "$TIMER"; clear_marker ;;
  status:host) show_timer ;;
  verify:host) systemctl --user is-active --quiet "$TIMER" && echo "$TIMER is active" ;;

  # ---- k3s: the host timer stays (its guards, schedule and publish step); the work runs in a pod ----
  # The weekly refresh is a heavy job: traction-control's job guard and central-ecu hold it back on a busy or hot
  # machine, and a post-step publishes the README pull request with the host's GitHub credentials. A CronJob
  # would bypass all three, so the timer and unit keep running them and only ExecStart changes: a removable
  # drop-in makes it run the job in K3s and wait. The CronJob stays suspended and serves as the template.
  up:k3s)
    require_cluster_tools
    timer_installed || {
      echo "$TIMER is not installed: k3s mode keeps the host timer as the trigger. Install it with Clockwork (see docs/deployment.md)" >&2
      exit 1
    }
    "$K3S_DIR/prepare-host.sh"
    "$K3S_DIR/build-image.sh"
    "$K3S_DIR/apply.sh"
    "$K3S_DIR/verify.sh"
    # Switch the unit over only after verify passed: until then the host runs the work as before.
    "$K3S_DIR/handover.sh" pod-on
    systemctl --user enable --now "$TIMER"
    set_marker k3s
    ;;
  down:k3s) "$0" --mode host up; echo "rolled back: the unit runs on the host again; the CronJob template is left in place (kubectl delete ns $NAMESPACE removes it)" ;;
  status:k3s) show_timer; kc -n "$NAMESPACE" get cronjob,pods 2>&1 || true ;;
  verify:k3s) "$K3S_DIR/verify.sh" ;;
esac
