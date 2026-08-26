#!/usr/bin/env bash
# 端到端验证：采一轮 → 聚合 → 校验库内数据与各 API 端点。
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "== 1) 采集一轮 =="
uv run gpumon collect --once

echo "== 2) 库内数据校验 =="
uv run python - <<'PY'
import sqlite3, time
from gpumon.config import db_path
c = sqlite3.connect(db_path()); c.row_factory = sqlite3.Row
now = int(time.time())
rows = c.execute("""SELECT h.key, COUNT(*) n, MAX(s.ts) ts
  FROM sample_gpu s JOIN gpu_card g ON g.id=s.gpu_id JOIN host h ON h.id=g.host_id
  WHERE s.ts > ?-120 GROUP BY h.key ORDER BY h.key""", (now,)).fetchall()
print("  最近2分钟每机采到卡数:")
ok = True
for r in rows:
    flag = "" if r["n"]>=1 else "  <-- 异常"
    print(f"    {r['key']:8s} {r['n']} 行  {flag}")
print("  rollup 行数:",
      dict((t, c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0])
           for t in ("rollup_gpu_5m","rollup_gpu_1h","rollup_host_1h")))
PY

echo "== 3) API 端点校验 =="
PORT=18852
.venv/bin/gpumon web --port $PORT >/tmp/gpumon_verify_web.log 2>&1 &
WP=$!; sleep 3
for ep in "/api/health" "/api/meta" "/api/collector/status" "/api/overview?window=24h" "/api/users/current"; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:$PORT$ep")
  echo "  $code  $ep"
done
kill $WP 2>/dev/null || true
echo "== 完成 =="
