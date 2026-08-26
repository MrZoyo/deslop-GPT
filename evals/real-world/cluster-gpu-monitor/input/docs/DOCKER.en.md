# Docker Compose Deployment

[简体中文](DOCKER.md) | English | [Documentation](README.en.md) | [Project home](../README.en.md)

The project supports two persistent deployment paths:

- [Native deployment](DEPLOYMENT.en.md): Python virtual environment, systemd, immutable releases,
  and Caddy.
- Docker Compose: one image runs separate collector, Web, and one-shot backup services.

This guide covers Docker Compose only. Both paths use the same configuration format and SQLite
database, but only one collector may write a database. Never start the container collector while a
native collector still uses the same data directory.

Containers run only on the monitor host and collect remote GPUs over SSH. They need no NVIDIA
Container Toolkit, `--privileged`, or host GPU device mounts.

## Services and trust boundaries

`compose.yaml` starts three roles from one image:

| Service | SSH directory | Configuration | Data directory | Network |
| --- | --- | --- | --- | --- |
| `collector` | read-only | read-only | read-write | outbound SSH only |
| `web` | not mounted | read-only | read-only | isolated network; host-loopback port only |
| `backup` | not mounted | read-only | read-write | disabled |

All services run as a non-root user with a read-only root filesystem, all capabilities dropped,
`no-new-privileges`, PID and memory limits, and log rotation. The Web application still has no
built-in authentication. Team access must pass through an authenticating HTTPS reverse proxy.

## Requirements

The monitor host needs:

- Linux and Docker Engine 24+.
- Docker Compose v2.24+, invoked as `docker compose`.
- Dedicated SSH configuration, `known_hosts`, and keys for every GPU node.
- Configuration and data directories on a local filesystem. Do not put SQLite on NFS or an object
  storage mount.

Target GPU nodes have the same requirements as native deployment: a regular account that can run
the vendor SMI tool, `ps`, `bash`, and coreutils.

## 1. Prepare configuration and data directories

Run from the repository root:

```bash
cp config/inventory.example.yaml config/inventory.yaml
cp config/settings.example.toml config/settings.toml
cp deploy/docker/.env.example .env
```

Edit `config/inventory.yaml` and `config/settings.toml`. Containers mount all of `config/` read-only
at `/state/config` and mount `data/` at `/state/data`. Git ignores real configuration, databases,
and `.env`; the Docker build context also uses an allowlist, so none enter the image build.

Production may keep state outside the checkout by setting absolute paths in `.env`:

```dotenv
GPUMON_CONFIG_DIR=/opt/gpu-monitor/config
GPUMON_DATA_DIR=/opt/gpu-monitor/data
```

The data directory must be writable by the UID/GID used inside the image.

## 2. Prepare a dedicated SSH directory

Do not mount your entire personal `~/.ssh` directory into the collector. Prepare a directory used
only by GPU Monitor and place only these files inside:

- `config`
- `known_hosts`
- A dedicated private key and its public key

The container home is fixed at `/home/gpumon`, so SSH configuration can keep home-relative key
paths:

```sshconfig
Host gpu-node-1
    HostName <NODE_ADDRESS>
    User <REMOTE_USER>
    IdentityFile ~/.ssh/id_ed25519_gpumon
    StrictHostKeyChecking yes
```

ProxyJump, multi-hop bastions, and host-key policy work like the
[native SSH setup](DEPLOYMENT.en.md#2-ssh-configuration-foundation-of-entire-deployment).
Addresses must be reachable from the container network. `127.0.0.1` in SSH configuration points
to the container itself, not the host.
The SSH directory is read-only inside the container. Populate `known_hosts` before starting the
collector instead of relying on `accept-new` to write during the first connection.

Recommended modes are `0700` for the directory, `0600` for private keys and `config`, and `0644`
for `known_hosts`. Set its absolute path in `.env`:

```dotenv
GPUMON_SSH_DIR=/absolute/path/to/gpumon-ssh
```

## 3. Match the container UID/GID

The image creates `gpumon` with UID/GID 1000 by default. Change `.env` to the IDs of the host user
that owns the SSH and data directories. Run `id -u` and `id -g` separately to inspect the current
user's values.

```dotenv
GPUMON_UID=1000
GPUMON_GID=1000
```

UID/GID values take effect at image build time. Run `docker compose build` again after changing
them. Do not loosen private-key permissions to work around an ID mismatch.

## 4. Build and test one collection round

Render the Compose model first to validate syntax and required variables:

```bash
docker compose config --quiet
docker compose build
```

Validate configuration without initiating SSH, then collect one round:

```bash
docker compose run --rm --no-deps collector config-check
docker compose run --rm --no-deps collector collect --once
```

The second command initializes SQLite, writes one sample round, and runs rollups. It exits nonzero
when every target fails. Fix SSH or remote dependencies before starting persistent services.

## 5. Start and access the dashboard

```bash
docker compose up -d collector web
docker compose ps
curl --max-time 5 -fsS http://127.0.0.1:8848/api/live
curl --max-time 5 -fsS http://127.0.0.1:8848/api/health
```

The default publishes only `127.0.0.1:8848`. Open `http://127.0.0.1:8848/` locally. From another
machine, create an SSH tunnel:

```bash
ssh -N -L 8848:127.0.0.1:8848 <monitor-host>
```

For team access, let host Caddy, Nginx, or another reverse proxy reach `127.0.0.1:8848` and provide
HTTPS plus authentication. Do not change `GPUMON_WEB_BIND` to `0.0.0.0` unless an outer network
layer already provides equivalent protection.

## 6. Routine operations

Read a bounded amount of recent logs:

```bash
docker compose logs --tail 100 collector
docker compose logs --tail 100 web
```

Restart both persistent services after changing inventory or settings so each process reloads its
configuration:

```bash
docker compose restart collector web
```

Stopping services preserves host configuration and data:

```bash
docker compose down
```

Never run `docker compose up --scale collector=2`. The SQLite design requires exactly one
collector.

## 7. Backups and scheduling

Run a manual backup through the one-shot, network-disabled backup service:

```bash
docker compose run --rm --no-deps backup
```

The SQLite backup API writes into the host's `data/backups/`, validates the new file, publishes it
atomically, then prunes old backups according to `keep_count`. Never copy live `gpumon.db`, WAL, or
SHM files directly.

Compose has no scheduler. In production, choose one host scheduler and invoke exactly this command
once per day:

```bash
cd /absolute/path/to/cluster-gpu-monitor && \
  /usr/bin/docker compose run --rm --no-deps backup backup --scheduled
```

`--scheduled` reads `backup.enabled` and exits successfully without a backup when disabled. Choose
one of systemd timer, cron, NAS task scheduler, or platform scheduler. Never enable more than one
backup schedule.

## 8. Upgrade and rollback

Back up the database and retain the current image under a local rollback tag:

```bash
docker compose run --rm --no-deps backup
docker image tag "$(docker compose images -q collector)" cluster-gpu-monitor:rollback
git pull --ff-only
docker compose build --pull
```

Update the collector first. Confirm fresh samples continue, then update Web:

```bash
docker compose up -d --no-deps collector
curl --max-time 5 -fsS http://127.0.0.1:8848/api/health
docker compose up -d --no-deps web
curl --max-time 5 -fsS http://127.0.0.1:8848/api/health
```

If the new version fails, restore both services from the retained image:

```bash
GPUMON_IMAGE=cluster-gpu-monitor:rollback \
  docker compose up -d --no-deps collector web
```

Keep the rollback running while diagnosing the new image. Never run old and new collectors
together.

## 9. Troubleshooting

### SSH permission errors

Confirm that `.env` UID/GID values match the SSH directory owner and private keys remain `0600`.
Inspect file metadata only; never paste private-key contents into logs, issues, or chat. Test one
alias from the collector container:

```bash
docker compose run --rm --no-deps --entrypoint ssh collector \
  -o BatchMode=yes -o ConnectTimeout=10 <ssh-alias> true
```

### Web does not open

Check the process, liveness endpoint, and bounded recent logs in order:

```bash
docker compose ps web
curl --max-time 5 -fsS http://127.0.0.1:8848/api/live
docker compose logs --tail 100 web
```

`/api/live` checks only the process. `/api/health` also checks configuration, the database, and
sample freshness.

### Data directory is not writable

Confirm `GPUMON_DATA_DIR` points to a local directory, its owner matches the UID/GID in `.env`, and
the collector data mount remains read-write. Do not hide permission errors by running the container
as root.

## Security checklist

- [ ] The build context is a clean public checkout, not a private overlay.
- [ ] Collector mounts only the dedicated SSH directory; Web and backup see no SSH files.
- [ ] Web publishes only to host loopback; external access passes through HTTPS and authentication.
- [ ] Configuration is read-only and Web data is read-only.
- [ ] SQLite stays on a local filesystem and exactly one collector runs.
- [ ] One scheduler triggers automatic backups and a usable file appears in `data/backups/`.
- [ ] No Docker socket, privileged mode, or extra capability is present.
