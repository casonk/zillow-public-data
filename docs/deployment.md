# Deployment modes: zillow-public-data

zillow-public-data runs three ways. You choose with one setting, and **only the `k3s` mode needs a cluster**. If you just
want to run it, you need Python and nothing else.

| Mode | What it is | Needs |
|---|---|---|
| `dev` (default) | one run in the foreground, no systemd, no cluster | the language runtime |
| `host` | the systemd user timer runs `refresh.py` | systemd |
| `k3s` | the same timer triggers the work, which runs in a pod | K3s, podman, kubectl, the in-cluster registry, and the host timer |

The application code is the same in all three: nothing under `src/` knows which mode it is in.

## Choose a mode

```bash
deploy/deploy.sh mode                  # print the mode in effect and where it came from
deploy/deploy.sh up                    # run it in that mode
deploy/deploy.sh status | verify | down
```

The mode is read from, first match wins:

1. `--mode dev|host|k3s` on the command line
2. `ZILLOW_DEPLOY_MODE` in the environment
3. `ZILLOW_DEPLOY_MODE` in `config/deploy.local.env` (copy `config/deploy.example.env`; it is gitignored)
4. `dev`

An unknown value, or a config file that cannot be read, is an error, never a silent fallback.

## What each mode does

### dev
`up` runs the job once in the foreground. `status` and `verify` check it without changing anything.

### host
`up` enables the systemd user timer (install it once with Clockwork; `up` says so if it is missing). `down` disables it.

### k3s
`up` refuses to start, and changes nothing, unless kubectl, podman and the in-cluster registry are present. Then it
builds the image (refusing uncommitted source), applies the manifests (the CronJob is created **suspended**), runs
`verify.sh` (which must pass), and only then disables the host timer and unsuspends the CronJob. A failed step
changes nothing: the timer keeps running.

## Switching

| From | To | Command |
|---|---|---|
| dev | host | `deploy/deploy.sh --mode host up` |
| host | k3s | `deploy/deploy.sh --mode k3s up` (verifies first, then hands over) |
| k3s | host | `deploy/deploy.sh --mode host up` (suspends the CronJob, re-enables the timer) |

`--mode k3s down` is the same as `--mode host up`. A marker in `~/.local/state/zillow-public-data/` records which mode last
held the work, so `host up` knows what to stop first.

## For contributors without K3s

- `pytest` needs no cluster: the deployment tests parse manifests and run the scripts against stub commands.
- Nothing under `deploy/k3s/` runs unless you select the `k3s` mode.
- This file, the scripts and their tests started from traction-control's `scripts/scaffold_deployment_modes.py`;
  the contract is in its `docs/deployment-modes.md`. Run `scripts/check_deployment_modes.py --repo .` to check.

## zillow-public-data specifics (k3s)

This is a heavy weekly job, so k3s mode differs from a plain CronJob hand-over:

- **The host timer stays the trigger.** The unit keeps its job guard (no run on a hot or busy machine),
  central-ecu, the 3 hour limit and the post-step that opens the README pull request with your GitHub credentials.
  A CronJob would bypass all of them.
- **Only `ExecStart` changes.** `deploy.sh --mode k3s up` installs a drop-in (`20-k3s-run.conf`) that runs
  `deploy/k3s/run-job.sh`: it creates one Job from the suspended CronJob template, streams its log into the
  journal and exits with the job's status. `--mode host up` removes the drop-in.
- **The pod needs one host and no credentials.** Egress is limited to `files.zillowstatic.com`; the host, the
  Kubernetes API and every other address are denied. `data/` and `viz/` are mounted read-write from this checkout,
  so the publish step reads the same files.
- **Prepare once.** `deploy/k3s/prepare-host.sh` labels `data/` and `viz/` for containers; its output says how to
  undo it with `restorecon -RF`.
