#!/usr/bin/env bash
# 远端探测脚本。经 `ssh <alias> bash -s` 从 stdin 喂入，远端不落地文件。
# 一次连接拿全部数据，用 ## 标记分段，便于鲁棒解析。
# 关键：LC_ALL=C 固定 locale（否则 free/数字会被本地化）；只用 coreutils + 厂商 smi + ps。
# __CPU_GAP__ 会被采集器替换为 settings.cpu_sample_gap_s（两次读 /proc/stat 的间隔）。
# __VENDOR_HINT__ 会被替换为 inventory 里主机的 vendor（nvidia/amd），留空则自动探测。
#
# 设计原则：**这里只做原样转发，不在远端做 JSON 解析**。
# AMD 的 rocm-smi / amd-smi 字段名跨 ROCm 版本变化很大，远端不一定有 jq；
# 把原始 JSON 整段吐回来，让 parse.py 用 Python 处理 —— 可单测、可兼容多版本。
export LC_ALL=C

echo "##META"
date +%s
hostname
nproc

echo "##LOADAVG"
cat /proc/loadavg

echo "##MEMINFO"
grep -E '^(MemTotal|MemAvailable):' /proc/meminfo   # 单位 kB

echo "##CPU1"
grep '^cpu ' /proc/stat
sleep __CPU_GAP__
echo "##CPU2"
grep '^cpu ' /proc/stat

# ---------------------------------------------------------------------------
# 厂商探测：inventory 给了 hint 就用它，否则看哪个 smi 真能跑通。
# 用 `command -v` + 一次实际调用双重确认 —— 装了驱动包但没卡的机器上
# nvidia-smi 存在却会报错，只查存在性会误判。
# ---------------------------------------------------------------------------
VENDOR_HINT="__VENDOR_HINT__"
VENDOR="none"
if [ -n "$VENDOR_HINT" ]; then
  VENDOR="$VENDOR_HINT"
elif command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L >/dev/null 2>&1; then
  VENDOR="nvidia"
elif command -v amd-smi >/dev/null 2>&1 && amd-smi list >/dev/null 2>&1; then
  VENDOR="amd"
elif command -v rocm-smi >/dev/null 2>&1 && rocm-smi --showid >/dev/null 2>&1; then
  VENDOR="amd"
fi

echo "##VENDOR"
echo "$VENDOR"

PIDS=""

if [ "$VENDOR" = "nvidia" ]; then
  echo "##GPU"
  nvidia-smi --query-gpu=index,uuid,name,utilization.gpu,utilization.memory,memory.used,memory.total,temperature.gpu,power.draw \
    --format=csv,noheader,nounits 2>/dev/null

  echo "##APPS"
  nvidia-smi --query-compute-apps=gpu_uuid,pid,used_memory --format=csv,noheader,nounits 2>/dev/null

  PIDS=$(nvidia-smi --query-compute-apps=pid --format=csv,noheader,nounits 2>/dev/null \
    | tr -d ' ' | grep -E '^[0-9]+$' | sort -u | paste -sd,)

elif [ "$VENDOR" = "amd" ]; then
  # amd-smi（ROCm 6+，rocm-smi 的继任者）优先；两者都吐原始 JSON 给 Python 解析。
  # static 拿 uuid/型号，metric 拿利用率/显存/温度/功耗，process 拿每卡进程。
  if command -v amd-smi >/dev/null 2>&1; then
    echo "##AMDSMI_STATIC"
    amd-smi static --json 2>/dev/null
    echo "##AMDSMI_METRIC"
    amd-smi metric --json 2>/dev/null
    echo "##AMDSMI_PROCESS"
    amd-smi process --json 2>/dev/null
  fi
  if command -v rocm-smi >/dev/null 2>&1; then
    # 老 ROCm 的回退路径。--showmeminfo vram 给的是字节，Python 侧换算成 MiB。
    echo "##ROCMSMI_JSON"
    rocm-smi --showid --showproductname --showuniqueid --showuse --showmemuse \
      --showmeminfo vram --showtemp --showpower --json 2>/dev/null
    # 进程→GPU 的映射：--showpidgpus 在部分版本才有，拿不到就只能留空（见 parse.py 注释）
    echo "##ROCMSMI_PIDS"
    rocm-smi --showpids --json 2>/dev/null
    echo "##ROCMSMI_PIDGPUS"
    rocm-smi --showpidgpus 2>/dev/null
  fi

  PIDS=$( { amd-smi process --json 2>/dev/null; rocm-smi --showpids 2>/dev/null; } \
    | grep -oE '"?(pid|PID)"?[":= ]+[0-9]+' | grep -oE '[0-9]+$' | sort -u | paste -sd,)
fi

echo "##PSMAP"
if [ -n "$PIDS" ]; then
  # user:32 —— 必须显式给宽度：`user=` 默认列宽 8，超长用户名会被 ps 截成
  # "superno+"（+ 是 ps 自己加的截断标记），落库后同一个人被当成两个用户。
  # -w/-ww 只放宽整行（对 args 列有效），不影响 user 列宽，不能替代此写法。
  ps -o pid=,user:32=,comm= -p "$PIDS" 2>/dev/null
fi

echo "##END"
