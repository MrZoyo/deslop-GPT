-- gpu-monitor SQLite schema
-- 时间统一为 epoch 秒（INTEGER, UTC）。事实表用 WITHOUT ROWID 按主键物理聚簇，
-- 使“某卡/某机过去 N 小时”的查询变成连续区间扫描。为将来迁 TimescaleDB 预留：
-- 首列时间、聚合表对齐 continuous aggregate、外键可平移。

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------------
-- 维度表（缓变，由 inventory 同步）
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cluster (
  id          INTEGER PRIMARY KEY,
  key         TEXT NOT NULL UNIQUE,          -- 稳定 key，如 'cluster-a'
  name        TEXT NOT NULL,
  sort_order  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS host (
  id            INTEGER PRIMARY KEY,
  cluster_id    INTEGER NOT NULL REFERENCES cluster(id),
  key           TEXT NOT NULL UNIQUE,        -- 'node-1'，历史按它关联，勿改
  ssh_alias     TEXT NOT NULL,               -- 'my-node-1'，采集用，可随部署机变
  display_name  TEXT NOT NULL,
  gpu_count     INTEGER NOT NULL,            -- 期望卡数，用于断卡检测
  meta_json     TEXT,
  sort_order    INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_host_cluster ON host(cluster_id);

CREATE TABLE IF NOT EXISTS gpu_card (
  id             INTEGER PRIMARY KEY,
  host_id        INTEGER NOT NULL REFERENCES host(id),
  gpu_index      INTEGER NOT NULL,           -- nvidia-smi index（展示用，重启可能变）
  uuid           TEXT NOT NULL UNIQUE,       -- GPU-xxxx，跨重启稳定，关联进程
  name           TEXT,
  mem_total_mib  INTEGER
);
CREATE INDEX IF NOT EXISTS ix_gpu_host ON gpu_card(host_id);

-- ---------------------------------------------------------------------------
-- 事实表（高频写）
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sample_gpu (
  gpu_id        INTEGER NOT NULL REFERENCES gpu_card(id),
  ts            INTEGER NOT NULL,
  util_gpu      INTEGER,
  util_mem      INTEGER,
  mem_used_mib  INTEGER,
  temp_c        INTEGER,
  power_w       REAL,
  PRIMARY KEY (gpu_id, ts)
) WITHOUT ROWID;
CREATE INDEX IF NOT EXISTS ix_sample_gpu_ts ON sample_gpu(ts);

CREATE TABLE IF NOT EXISTS sample_proc (
  gpu_id        INTEGER NOT NULL REFERENCES gpu_card(id),
  ts            INTEGER NOT NULL,
  pid           INTEGER NOT NULL,
  username      TEXT,
  comm          TEXT,                        -- 仅进程名，不存命令行参数
  mem_used_mib  INTEGER,
  PRIMARY KEY (gpu_id, ts, pid)
) WITHOUT ROWID;
CREATE INDEX IF NOT EXISTS ix_proc_user_ts ON sample_proc(username, ts);
CREATE INDEX IF NOT EXISTS ix_proc_ts ON sample_proc(ts);
-- 使用人排行/榜（get_users_ranking / get_users_top）按 ts 区间扫 sample_proc 再按
-- username 聚合。只有 ix_proc_ts(ts) 时，命中的每一行都要回表取 username/gpu_id
-- ——1 个月窗口 = 数百万次随机回表。下面这条把这三列都带上做成**覆盖索引**，
-- 扫描全在索引内完成、不回表：生产库 1 月窗口 52s → 3.7s。
-- 代价：磁盘 +93MB（约每百万行 25MB），写入多维护一个索引。
CREATE INDEX IF NOT EXISTS ix_proc_ts_cover ON sample_proc(ts, username, gpu_id, mem_used_mib);

-- ⚠️ 不要对本库跑 ANALYZE。实测（生产库副本，1 月排行窗口）：
--   无 stats + 覆盖索引 = 3.7s   ← 现状，最快
--   有 stats + 覆盖索引 = 60s    ← 慢 16 倍
-- 有 sqlite_stat1 时优化器改走 "SCAN host → gpu_card → sample_proc 主键区间"，
-- 即按 72 张卡各扫一遍 30 天区间，反而放弃了覆盖索引的一次顺序扫。
-- 若误跑过 ANALYZE，用 `DROP TABLE sqlite_stat1;` 删掉统计表即可恢复。

CREATE TABLE IF NOT EXISTS sample_host (
  host_id        INTEGER NOT NULL REFERENCES host(id),
  ts             INTEGER NOT NULL,
  ncpu           INTEGER,
  load1          REAL,
  load5          REAL,
  load15         REAL,
  cpu_util_pct   REAL,
  mem_total_mib  INTEGER,
  mem_avail_mib  INTEGER,
  mem_used_mib   INTEGER,
  PRIMARY KEY (host_id, ts)
) WITHOUT ROWID;
CREATE INDEX IF NOT EXISTS ix_sample_host_ts ON sample_host(ts);

-- ---------------------------------------------------------------------------
-- 聚合表（rollup）。n=该桶样本数，用于加权再聚合 + 断档检测。
-- bucket_ts = ts - ts % 桶宽，桶起点。
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rollup_gpu_5m (
  gpu_id        INTEGER NOT NULL REFERENCES gpu_card(id),
  bucket_ts     INTEGER NOT NULL,
  n             INTEGER NOT NULL,
  util_gpu_avg  REAL, util_gpu_max INTEGER,
  util_mem_avg  REAL,
  mem_used_avg  REAL, mem_used_max INTEGER,
  temp_avg      REAL, temp_max INTEGER,
  power_avg     REAL,
  PRIMARY KEY (gpu_id, bucket_ts)
) WITHOUT ROWID;
CREATE INDEX IF NOT EXISTS ix_rollup_gpu_5m_bucket ON rollup_gpu_5m(bucket_ts);

CREATE TABLE IF NOT EXISTS rollup_gpu_1h (
  gpu_id        INTEGER NOT NULL REFERENCES gpu_card(id),
  bucket_ts     INTEGER NOT NULL,
  n             INTEGER NOT NULL,
  util_gpu_avg  REAL, util_gpu_max INTEGER,
  util_mem_avg  REAL,
  mem_used_avg  REAL, mem_used_max INTEGER,
  temp_avg      REAL, temp_max INTEGER,
  power_avg     REAL,
  PRIMARY KEY (gpu_id, bucket_ts)
) WITHOUT ROWID;
CREATE INDEX IF NOT EXISTS ix_rollup_gpu_1h_bucket ON rollup_gpu_1h(bucket_ts);

CREATE TABLE IF NOT EXISTS rollup_host_1h (
  host_id       INTEGER NOT NULL REFERENCES host(id),
  bucket_ts     INTEGER NOT NULL,
  n             INTEGER NOT NULL,
  cpu_util_avg  REAL,
  load1_avg     REAL,
  mem_used_avg  REAL,
  PRIMARY KEY (host_id, bucket_ts)
) WITHOUT ROWID;

-- ---------------------------------------------------------------------------
-- 采集状态（每机一行，采集器每轮更新；供健康灯/掉线判断）
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS collector_status (
  host_id      INTEGER PRIMARY KEY REFERENCES host(id),
  last_try_ts  INTEGER,
  last_ok_ts   INTEGER,
  gpus_seen    INTEGER,
  consec_fail  INTEGER NOT NULL DEFAULT 0,
  last_error   TEXT
);

-- 聚合进度水位（避免每次全表扫；记录已聚合到的 bucket）
CREATE TABLE IF NOT EXISTS rollup_state (
  name        TEXT PRIMARY KEY,    -- 'gpu_5m' / 'gpu_1h' / 'host_1h'
  watermark   INTEGER NOT NULL DEFAULT 0   -- 已封口处理到的 bucket_ts
);
