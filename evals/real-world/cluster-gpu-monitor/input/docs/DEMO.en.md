# Demo Guide

[简体中文](DEMO.md) | English | [Documentation](README.en.md) | [Live demo](https://mrzoyo.github.io/cluster-gpu-monitor/)

The demo tools create fictional topology, usernames, and GPU history without any GPU nodes. Use
them to evaluate the application locally or export the real frontend as a fully static site.

> Never use real inventory, settings, or a production database for public static export. Exported
> JSON contains display names, host metadata, usernames, and process names from its inputs.

## Run fictional data locally

This procedure uses a temporary state root and does not overwrite repository configuration:

```bash
uv sync

DEMO_ROOT="$(mktemp -d)"
uv run python scripts/gen_demo_db.py \
  --scale small --days 3 \
  --db "$DEMO_ROOT/data/demo.db" \
  --inventory "$DEMO_ROOT/config/inventory.demo.yaml"

cp "$DEMO_ROOT/config/inventory.demo.yaml" "$DEMO_ROOT/config/inventory.yaml"
sed 's#path = "data/gpumon.db"#path = "data/demo.db"#' \
  config/settings.example.toml > "$DEMO_ROOT/config/settings.demo.toml"
cp "$DEMO_ROOT/config/settings.demo.toml" "$DEMO_ROOT/config/settings.toml"

GPUMON_ROOT="$DEMO_ROOT" uv run gpumon config-check
GPUMON_ROOT="$DEMO_ROOT" uv run gpumon web
```

Open `http://127.0.0.1:8848/`. After stopping the Web process, you may remove the temporary
directory printed by your shell; it is not required by the project.

### Scale and time range

| Option | Topology | Use case |
| --- | --- | --- |
| `--scale small` | 2 capacity domains, 3 clusters, 6 hosts, 48 GPUs | Quick evaluation and normal development |
| `--scale large` | 4 capacity domains, 9 clusters, 32 hosts, 256 GPUs | Large-page and query-performance checks |

Three days provide usable curves for the 12h, 24h, 48h, and 72h windows. Longer windows correctly
show that data is still accumulating. Generating 31 days can create millions of rows and a
gigabyte-scale database; use it only when monthly-window validation is necessary.

Fixtures cover saturated GPUs, idle-but-occupied cards, an offline host, a missing card, planned and
retired capacity, AMD, and folded badges. `--seed` controls reproducibility and has a fixed default.

## Export a static site

After generating the data above:

```bash
uv run python scripts/export_static_demo.py \
  --db "$DEMO_ROOT/data/demo.db" \
  --inventory "$DEMO_ROOT/config/inventory.demo.yaml" \
  --settings "$DEMO_ROOT/config/settings.demo.toml" \
  --out dist/demo

cd dist/demo
python3 -m http.server 8080
```

Open `http://127.0.0.1:8080/`. If the output already exists, `--force` works only after the exporter
confirms that the directory carries its marker.

The exporter:

1. Calls the real API code at the timestamp of the final sample and stores JSON responses.
2. Copies the unchanged frontend and injects a small shim that maps `/api/*` to those JSON files.
3. Decimates each series to at most 300 points and bundles it by scope, metric, and window.
4. Freezes relative time so the static site does not appear offline several days later.

The result has no backend, SSH access, or database write capability. It is a read-only snapshot of
one moment.

## Publish to GitHub Pages

The repository's [demo workflow](../.github/workflows/demo.yml) generates the large three-day
dataset, exports the site, and uploads it to GitHub Pages. Neither the generated database nor the
static output is committed to Git.

Changes to the frontend, API, demo fixtures, or generation/export scripts trigger the workflow on
push to `main`. It can also be started manually through `workflow_dispatch`.

## Destructive-operation guards

Both tools fail closed by default:

- The generator rejects runtime files, example configuration, dangerous paths, and databases named
  `gpumon.db`.
- `--force` can replace only correctly marked synthetic demo data.
- The exporter accepts only a complete generated database and matching marked inventory by default.
- Output cannot be a home, repository, runtime, or source directory. Recursive replacement is
  allowed only for a previously marked output.
- `--allow-unmarked-inputs` bypasses the generator-marker requirement but not dangerous-path checks.

Use `--allow-unmarked-inputs` only for deliberately constructed data that you have verified contains
no real information. Do not use it as a shortcut for production data.
