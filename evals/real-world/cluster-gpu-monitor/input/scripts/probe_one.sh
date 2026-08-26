#!/usr/bin/env bash
# 调试：对单台机器跑一次远端探测，打印原始分段输出。
# 拿到新机器（尤其 AMD）时先跑这个，确认 ##VENDOR / ##GPU / ##APPS 段有内容再接入 inventory。
# 用法: scripts/probe_one.sh <ssh别名> [cpu间隔秒] [vendor:nvidia|amd]
set -euo pipefail
alias="${1:?用法: probe_one.sh <ssh别名> [cpu间隔秒] [vendor]}"
gap="${2:-1}"
vendor="${3:-}"          # 留空 = 让远端自动探测
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
sed -e "s/__CPU_GAP__/$gap/" -e "s/__VENDOR_HINT__/$vendor/" \
  "$ROOT/src/gpumon/collector/remote_probe.sh" \
  | ssh -o BatchMode=yes -o ConnectTimeout=8 "$alias" bash -s
