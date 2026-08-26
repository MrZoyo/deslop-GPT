# Architecture and Trade-offs

[简体中文](ARCHITECTURE.md) | English | [Documentation](README.en.md) | [Project home](../README.en.md)

This document describes current behavior, metric semantics, and trust boundaries. See the
[configuration reference](CONFIGURATION.en.md) for fields and the
[deployment guide](DEPLOYMENT.en.md) for installation commands.

## Goals and non-goals

Cluster GPU Monitor targets a handful to a few dozen self-managed GPU servers without a shared
scheduler. It prioritizes:

- Collecting through the central host's existing SSH configuration without installing agents.
- Retaining long-term utilization and attributing VRAM occupancy to operating-system usernames.
- Supporting capacity planning with a small self-hosted service rather than a full telemetry stack.

It does not provide second-level alerts, scheduling, quotas, audit-grade identity mapping, or
billing. A single SQLite service is also not intended for thousand-node high-frequency telemetry.

## Data flow

```text
inventory.yaml + ~/.ssh/config
              │
              ▼
Central collector ── ssh <alias> bash -s ──► GPU nodes
              │                              nvidia-smi / amd-smi / rocm-smi
              │                              ps + /proc (no remote files)
              ▼
SQLite: dimensions + raw samples + 5-minute / 1-hour rollups
              │
              ▼
Read-only FastAPI ──► vanilla HTML / JavaScript / bundled ECharts
```

`inventory.yaml` defines logical topology and stable identifiers. Addresses, ports, accounts,
keys, and `ProxyJump` stay in the collector account's `~/.ssh/config`. Changing a network path
does not change database identity.

## Collection model

Each round processes only `active` hosts:

1. Assign one epoch-second timestamp to the entire round so samples align across hosts.
2. Open one system OpenSSH connection per host within the `max_concurrency` boundary.
3. Run `remote_probe.sh` from stdin and fetch GPU, process, CPU, memory, and load data together.
4. Parse and validate the output centrally, then write the round in one SQLite transaction.
5. Record a failed host independently without blocking successful hosts.

When `vendor` is unset, the remote probe tries NVIDIA and AMD tools in order on every round. A
working NVIDIA host therefore runs one extra `nvidia-smi -L`. Set a known, stable vendor to reduce
SMI calls on the target; leave it unset when the vendor is unknown or the hardware may change. The
NVIDIA path has production history. The AMD parser has synthetic fixtures but still needs
validation on real hardware.

Remote output is untrusted input. SSH has connection, total-time, and byte limits, and parsed GPU
and process objects have per-host and per-round limits. Abnormal process volume may be omitted
while preserving GPU and host metrics and recording a collector warning.

## Topology and lifecycle

The logical hierarchy is capacity domain → cluster → host → discovered GPUs. Identifiers serve
different purposes:

| Identifier | Purpose | Change policy |
| --- | --- | --- |
| Cluster/host `key` | Historical database identity | Do not change after deployment |
| `ssh_alias` | Lookup key in `~/.ssh/config` | Change when addresses or bastions change |
| `display_name` | UI label | Change freely |
| GPU UUID | Associates card and process samples | Discovered from vendor tools |

Status semantics:

- `active`: collected and included in current statistics and liveness.
- `planned`: capacity placeholder only; shown as planned capacity, but not collected or included in
  utilization-coverage denominators.
- `retired`: no longer collected and hidden from the UI; database rows and samples remain, while
  current statistics and user rankings exclude the host.

Removing inventory entries cannot express these states and makes historical ownership harder to
interpret. Retire resources by status instead.

## Storage and rollups

SQLite runs in WAL mode. The collector is the only writer and keeps a long-lived connection. Each
Web query opens a read-only connection protected by both `mode=ro` and
`PRAGMA query_only=ON`.

| Data | Table | Primary use |
| --- | --- | --- |
| Raw GPU samples | `sample_gpu` | Current values, recent utilization, and rollup source |
| Raw process samples | `sample_proc` | Current users and user GPU hours |
| Raw host samples | `sample_host` | CPU, memory, and load |
| 5-minute GPU rollups | `rollup_gpu_5m` | 12-hour and 24-hour windows |
| 1-hour GPU rollups | `rollup_gpu_1h` | 48-hour through 1-month windows |
| 1-hour host rollups | `rollup_host_1h` | Historical host metrics |

Rollups process only closed time buckets and advance incrementally with watermarks. The persistent
collector advances 5-minute rollups every minute, 1-hour rollups every five minutes, and retention
cleanup every hour. `gpumon rollup-once` runs the same rollup and cleanup logic manually.

### Query windows

The UI supports `12h`, `24h`, `48h`, `72h`, `1w`, `2w`, and `1m`:

| Window | Query source | Bucket width |
| --- | --- | --- |
| `12h`, `24h` | `rollup_gpu_5m` | 5 minutes |
| `48h`, `72h`, `1w`, `2w`, `1m` | `rollup_gpu_1h` | 1 hour |
| Every user-ranking window | `sample_proc` | Raw poll interval |

`raw_days` must therefore cover the longest 30-day ranking. Validation currently requires at
least 31 days and defaults to 35. See the
[configuration reference](CONFIGURATION.en.md#how-to-set-retention-days-theres-a-gotcha) for the
complete retention rules.

## Metric semantics

“Current,” “recent,” and “selected-window average” are intentionally different values:

| UI value | Source and rule | Purpose |
| --- | --- | --- |
| Instantaneous | Latest raw sample for each GPU | Tooltip and single-GPU details |
| Recent utilization | Mean of the last 10 minutes; forced to zero when the latest three samples are all `≤5%` | GPU card value, color, and busy state |
| Window average | Sample-count-weighted rollup mean over the selected window | Capacity planning and historical comparison |

Training loads often oscillate between 0 and 100 between steps. The recent value avoids treating a
short gap as idle, while the three-sample rule lets a stopped job fall to zero quickly. The current
busy threshold is recent utilization `≥10%`.

An idle-but-occupied card must have a user process holding more than zero VRAM and recent
utilization below `5%`. A process with no VRAM does not count as a user, and a missing recent value
is never guessed to be idle-but-occupied.

`coverage` compares actual samples with expected GPUs × window length ÷ configured poll interval.
It reveals disconnects and newly added capacity. Treat a low-coverage average as incomplete.

### Liveness and freshness

The current implementation retains two independent gates:

- `/api/collector/status` considers a host online when its latest successful collection is no more
  than **120 seconds** old.
- Raw sample freshness is `max(120 seconds, 4 × poll_interval_s)`.

The overview returns current values and users only when the host is online and its sample is still
fresh. Otherwise it returns null instead of stale occupancy. These thresholds are not unified;
changing the poll interval does not change the fixed 120-second online window.

### GPU hours

Attribution uses the operating-system username reported by `ps`. At each poll, multiple PIDs for
the same username on the same GPU are deduplicated, then add `poll_interval_s / 3600`. If several
users share one GPU, each receives the full interval; time is not divided among them.

This is useful for usage trends, not billing. SSH failures undercount, actual round timing can
differ slightly from the configured interval, and usernames do not model projects, jobs, or real
identities.

## Security and privacy boundaries

A production deployment should separate three trust domains:

| Component | Required access | Access it should not have |
| --- | --- | --- |
| Collector / backup | SSH configuration and keys, SQLite write access | Public ingress |
| Web | Read-only configuration and SQLite | SSH home, keys, database writes |
| Caddy / network layer | TLS, authentication, source restrictions | Collection credentials |

The Web application has **no built-in login or authorization system**. It binds to `127.0.0.1` by
default. Team access should use an authenticating HTTPS reverse proxy; personal access can use an
SSH tunnel. Interactive FastAPI documentation is disabled by default in production. Expensive
queries also have concurrency, queue, execution-time, and result-count limits.

The public API removes SSH aliases and GPU UUIDs, but may still return display names, host metadata,
usernames, and process names. `mask_users=true` is readable masking, not irreversible anonymization
and not access control. Never commit real inventory, settings, SSH configuration, keys, or a
production database to the public repository.
