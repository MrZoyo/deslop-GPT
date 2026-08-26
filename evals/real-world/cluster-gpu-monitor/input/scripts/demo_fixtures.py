#!/usr/bin/env python3
"""演示数据的「文案层」—— 只放数据，不含任何生成逻辑。

拆出来单独一个文件的原因：造数脚本（gen_demo_db.py）关心的是时间序列怎么编、
聚合表怎么算；而这里关心的是名字好不好笑、拓扑够不够刁钻。两件事改动频率完全
不一样，混在一起每次改个集群名都要重读几百行造数代码。

三个基本立场：
  - 名字一眼假。域名/集群名/卡型号全是谐音梗与虚构型号（H250 / B666 / MI999 …），
    确保任何人打开演示站都不会误以为这是某个真实机房的实时数据。
  - 拓扑刻意不均匀。一个域挂 3 个集群、另一个域只有 1 个，就是为了压配色轮转、
    标签折叠（>3 枚折成 "+N"）、空集群占位这些只在畸形拓扑下才暴露的分支。
  - 数字必须对得上。大集合精确 32 机 / 256 卡，SMALL 精确 6 机 / 48 卡；
    validate() 会把这两个总数连同 key 唯一性一起断言，改数据后跑一遍即可。

用户名一律 ASCII（拼音梗），因为它们最终要当 Linux 用户名进 sample_proc 表，
中文进去排行榜和 ps 输出都会炸。

独立可跑：`python scripts/demo_fixtures.py` → 跑 validate() 并打印规模摘要。
"""
from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# 合法取值。与 gpumon.models 保持一致，但这里刻意不 import ——
# 本文件是纯数据，要能在没装包的环境里直接 python 跑通自检。
# 若哪天 models.PALETTES 增删了色带，validate() 会在演示站构建时先报出来。
# ---------------------------------------------------------------------------
PALETTES = ("lime", "violet", "azure", "amber", "rose", "teal", "indigo", "slate")
TONES = ("cyan", "gold", "green", "violet", "neutral")
STATUSES = ("active", "planned", "retired")
VENDORS = ("nvidia", "amd")
STYLES = ("trainer", "squatter", "burster", "tourist")


def localized(zh: str, en: str) -> dict[str, str]:
    """按回退优先级生成 demo 文案；中文故意放第一项。"""
    return {"zh": zh, "en": en}


# Linux 用户名字符集：小写字母开头，总长 ≤32
USERNAME_RE = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")

# 目标规模，validate() 按这两个数断言（改拓扑时同步改这里）
LARGE_GPUS = 256
SMALL_GPUS = 48

# ---------------------------------------------------------------------------
# 标签库 —— 一处定义，算力域/集群按 key 引用，改一次全站生效。
# 演示站刻意让「自建」「液冷」这类通用属性被多处复用，
# 只在真正一次性的标签上才内联写（见 CLUSTERS 里的少数几处）。
# ---------------------------------------------------------------------------
BADGE_LIBRARY: list[dict] = [
    {"key": "self-built",
     "text": localized("自建", "Self-built"),
     "mark": "◆", "tone": "cyan",
     "tooltip": localized(
         "自己装的机，账号找隔壁工位申请",
         "Built in-house; ask the next desk over for access.")},
    {"key": "rented",
     "text": localized("租用", "Rented"),
     "mark": "◆", "tone": "gold",
     "tooltip": localized(
         "按小时计费，跑完记得把进程杀干净",
         "Billed by the hour. Stop your jobs when you're done.")},
    {"key": "partner",
     "text": localized("合作方", "Partner"),
     "mark": "◆", "tone": "cyan",
     "tooltip": localized(
         "对方运维代管，报修走工单",
         "Managed by partner ops; submit a ticket for repairs.")},
    {"key": "non-blocking",
     "text": localized("无阻塞网络", "Non-blocking fabric"),
     "mark": None, "tone": "green",
     "tooltip": localized(
         "跨机训练不掉速，理论上",
         "Cross-node training keeps its speed—in theory.")},
    {"key": "liquid-cooling",
     "text": localized("液冷", "Liquid-cooled"),
     "mark": None, "tone": "violet",
     "tooltip": localized(
         "水管走在天花板上，抬头请注意",
         "Pipes overhead—mind your head.")},
    {"key": "legacy",
     "text": localized("祖传", "Heirloom"),
     "mark": "◆", "tone": "gold",
     "tooltip": localized(
         "上一任的上一任装的，驱动没人敢升",
         "Installed two maintainers ago. Nobody dares update the drivers.")},
    {"key": "summer-cap",
     "text": localized("夏季限功耗", "Summer power cap"),
     "mark": "▲", "tone": "gold",
     "tooltip": localized(
         "空调压不住时自动降频，别以为是卡坏了",
         "Auto-throttles when the AC falls behind; the GPUs are fine.")},
    {"key": "no-mining",
     "text": localized("禁止挖矿", "No mining"),
     "mark": None, "tone": "neutral",
     "tooltip": localized(
         "写在墙上了，但还是有人试",
         "It's on the wall. Someone still tries.")},
    {"key": "small-vram",
     "text": localized("显存偏小", "Small VRAM"),
     "mark": None, "tone": "neutral",
     "tooltip": localized(
         "跑大模型会 OOM，跑小实验正好",
         "Too small for giant models; just right for small experiments.")},
    {"key": "door-permit",
     "text": localized("门禁报备", "Access notice"),
     "mark": None, "tone": "neutral",
     "tooltip": localized(
         "进机房要提前三天报备，刷卡进不去",
         "Apply three days ahead; an unplanned badge tap won't get you in.")},
    {"key": "book-ahead",
     "text": localized("需预约", "Reservation required"),
     "mark": None, "tone": "gold",
     "tooltip": localized(
         "长期满载，用之前先在群里喊一声",
         "Usually full; give the team a heads-up before use.")},
]

# ---------------------------------------------------------------------------
# 算力域（第一层）。palette 全部显式指定，不走自动轮转 ——
# 演示站的截图要稳定，自动轮转会随 sort_order 变动而换色。
# badges 引用 BADGE_LIBRARY 里的 key，验证「算力域也能挂标签」这条路径。
# ---------------------------------------------------------------------------
DOMAINS: list[dict] = [
    {
        "key": "yinshan",
        "name": "银山算力域",
        "palette": "lime",
        "sort_order": 1,
        "description": localized(
            "自建机房。空调是去年双十一买的，夏天限功耗跑。",
            "Self-built server room. The AC was last year's Singles' Day deal, "
            "so summer workloads run with a power cap."),
        "badges": ["self-built", "summer-cap"],
    },
    {
        "key": "awaimama",
        "name": "阿外妈妈算力域",
        "palette": "violet",
        "sort_order": 2,
        "description": localized(
            "租的。按小时计费，月底账单一出全组集体沉默。",
            "Rented by the hour. When the month-end bill arrives, the whole team goes quiet."),
        "badges": ["rented"],
    },
    {
        "key": "longguo-dianxin",
        "name": "龙国电信算力域",
        "palette": "azure",
        "sort_order": 3,
        "description": localized(
            "合作方提供，带宽管够，进机房要提前三天报备。",
            "Partner-provided, with bandwidth to spare. Server-room visits need three days' notice."),
        "badges": ["partner", "door-permit"],
    },
    {
        "key": "caotai",
        "name": "草台算力域",
        "palette": "amber",
        "sort_order": 4,
        "description": localized(
            "各处捡来的边角料，型号全不一样，能跑就行。",
            "Spare parts gathered from everywhere. No two models alike; if it runs, it stays."),
    },
]

# ---------------------------------------------------------------------------
# 集群（第二层）+ 服务器（第三层）。
#
# 分布刻意畸形：银山 3 个、草台 3 个、龙国电信 2 个、阿外妈妈只有 1 个（但那 1 个
# 独占 104 卡）。这种「域数量少但卡多」的形状最容易把堆叠条和配色轮转搞乱。
#
# 主机 key 全局唯一（不只是集群内唯一）—— 项目的 _validate_unique_keys 就这么查，
# 历史数据也按主机 key 关联，撞 key 会让两台机器的曲线糊在一起。
#
# gpus_per_host 大多是 8；B666 那两台按 16 卡整机算（一机双托盘的梗），
# 野卡 4 卡、T404 2 卡，凑出 32 机 × 平均 8 卡 = 256 的同时保留卡数不齐的形状。
# ---------------------------------------------------------------------------
CLUSTERS: list[dict] = [
    # 银山 1/3：主力集群，标签故意挂 5 枚，用来验证 ">3 枚折叠成 +N" 的路径
    {
        "key": "yinshan-h250-4",
        "name": "4机H250集群",
        "domain": "yinshan",
        "sort_order": 1,
        "status": "active",
        "vendor": "nvidia",
        "gpu_model": "NVIDIA H250 141GB",
        "gpus_per_host": 8,
        "hosts": [
            {"key": "ys-h250-1", "name": "银山-01"},
            {"key": "ys-h250-2", "name": "银山-02"},
            {"key": "ys-h250-3", "name": "银山-03"},
            {"key": "ys-h250-4", "name": "银山-04（风扇最响）"},
        ],
        # 5 枚全部走库引用，验证 ">3 枚折叠成 +N" 同时验证复用
        "badges": ["self-built", "non-blocking", "liquid-cooling",
                   "summer-cap", "no-mining"],
        "note": localized(
            "全域最好的卡，也是最抢不到的卡。",
            "The best GPUs in the group—and the hardest to reserve."),
    },

    # 银山 2/3：双机 16 卡整机，标签 0 枚（验证卡片标题无标签时的排版）
    {
        "key": "yinshan-b666-2",
        "name": "双机B666集群",
        "domain": "yinshan",
        "sort_order": 2,
        "status": "active",
        "vendor": "nvidia",
        "gpu_model": "NVIDIA B666 192GB",
        "gpus_per_host": 16,
        "hosts": [
            {"key": "ys-b666-1", "name": "六六大顺-01"},
            {"key": "ys-b666-2", "name": "六六大顺-02"},
        ],
        "badges": [],
        "note": localized(
            "一机双托盘 16 卡，进机房要走货梯。",
            "Sixteen GPUs on two trays per host. Use the freight elevator."),
    },

    # 银山 3/3：祖传老卡，八卡机，显存小，专门用来演示「显存打满但利用率 0」
    {
        "key": "yinshan-zuchuan-3",
        "name": "八卡祖传集群",
        "domain": "yinshan",
        "sort_order": 3,
        "status": "active",
        "vendor": "nvidia",
        "gpu_model": "NVIDIA V180 32GB",
        "gpus_per_host": 8,
        "hosts": [
            {"key": "ys-zc-1", "name": "祖传-01"},
            {"key": "ys-zc-2", "name": "祖传-02"},
            {"key": "ys-zc-3", "name": "祖传-03（重启大师）"},
        ],
        "badges": ["legacy", "small-vram"],
        "note": localized(
            "谁也说不清是哪年买的，但它一直在跑。",
            "Nobody knows when it was bought, but it keeps running."),
    },

    # 阿外妈妈 1/1：全演示站最大的一坨，13 机 104 卡。
    # 一个域只挂一个集群、且这个集群占了总量四成 —— 堆叠条和排行榜的极端形状。
    {
        "key": "awaimama-a101-13",
        "name": "13机A101集群",
        "domain": "awaimama",
        "sort_order": 11,
        "status": "active",
        "vendor": "nvidia",
        "gpu_model": "NVIDIA A101 80GB",
        "gpus_per_host": 8,
        "hosts": [
            {"key": "awm-a101-01", "name": "外婆家-01"},
            {"key": "awm-a101-02", "name": "外婆家-02"},
            {"key": "awm-a101-03", "name": "外婆家-03"},
            {"key": "awm-a101-04", "name": "外婆家-04"},
            {"key": "awm-a101-05", "name": "外婆家-05"},
            {"key": "awm-a101-06", "name": "外婆家-06"},
            {"key": "awm-a101-07", "name": "外婆家-07"},
            {"key": "awm-a101-08", "name": "外婆家-08"},
            {"key": "awm-a101-09", "name": "外婆家-09"},
            {"key": "awm-a101-10", "name": "外婆家-10"},
            {"key": "awm-a101-11", "name": "外婆家-11"},
            {"key": "awm-a101-12", "name": "外婆家-12"},
            {"key": "awm-a101-13", "name": "外婆家-13（计费最贵）"},
        ],
        "badges": [
            "rented",
            "book-ahead",
            {"text": localized("月底到期", "Expires month-end"),
             "mark": None, "tone": "neutral",
             "tooltip": localized(
                 "续不续要等审批，别把长任务排到下月",
                 "Renewal is pending; don't schedule long jobs into next month.")},
        ],
        "note": localized(
            "卡多但按小时烧钱，空占检测主要就是给它用的。",
            "Plenty of GPUs, all billed by the hour. "
            "Idle-allocation detection earns its keep here."),
    },

    # 龙国电信 1/2：小而稳，SMALL 集合的主力
    {
        "key": "longguo-h250s-2",
        "name": "双机H250S集群",
        "domain": "longguo-dianxin",
        "sort_order": 21,
        "status": "active",
        "vendor": "nvidia",
        "gpu_model": "NVIDIA H250S 141GB",
        "gpus_per_host": 8,
        "hosts": [
            {"key": "lg-h250s-1", "name": "电信-01"},
            {"key": "lg-h250s-2", "name": "电信-02"},
        ],
        "badges": [
            "partner",
            "non-blocking",
            "door-permit",
        ],
        "note": localized(
            "机房在楼下，但门禁要提前三天报备。",
            "The server room is downstairs, but access needs three days' notice."),
    },

    # 龙国电信 2/2：唯一的 AMD 集群，ROCm 路径专用
    {
        "key": "longguo-mi999-1",
        "name": "单机MI999集群",
        "domain": "longguo-dianxin",
        "sort_order": 22,
        "status": "active",
        "vendor": "amd",
        "gpu_model": "AMD Instinct MI999 256GB",
        "gpus_per_host": 8,
        "hosts": [
            {"key": "lg-mi999-1", "name": "红队-01"},
        ],
        # 混用：库引用 + 内联一次性标签（ROCm/试水 只此一处，不进库）
        "badges": [
            "partner",
            {"text": "ROCm", "mark": None, "tone": "gold",
             "tooltip": localized(
                 "得装 ROCm 版框架，CUDA 代码搬过来要改",
                 "Requires a ROCm build; CUDA workloads may need changes.")},
            {"text": localized("试水", "Trial run"),
             "mark": None, "tone": "neutral",
             "tooltip": localized(
                 "先跑一台看看，好用再加",
                 "Start with one machine; scale out if it behaves.")},
        ],
        "note": localized(
            "全站唯一 AMD，采集走 rocm-smi 分支。",
            "The demo's only AMD cluster; collection uses the rocm-smi path."),
    },

    # 草台 1/3：4 卡野卡机，卡数不是 8 的整数倍，用来抓「默认 8 卡」的硬编码
    {
        "key": "caotai-yeka-1",
        "name": "单机四卡野卡集群",
        "domain": "caotai",
        "sort_order": 31,
        "status": "active",
        "vendor": "nvidia",
        "gpu_model": "NVIDIA RTX 6090 24GB",
        "gpus_per_host": 4,
        "hosts": [
            {"key": "ct-yeka-1", "name": "野卡-01（放在工位下）"},
        ],
        "badges": [
            {"text": localized("非机房", "Outside server room"),
             "mark": "▲", "tone": "gold",
             "tooltip": localized(
                 "就在工位底下，有人踢到电源线过",
                 "It lives under a desk; the power cable has met a few shoes.")},
        ],
        "note": localized(
            "卡数 4 不是 8，专门用来抓写死 8 卡的地方。",
            "Four GPUs, not eight—built to catch hard-coded assumptions."),
    },

    # 草台 2/3：已退役。采集器不再探测，但 DB 行和历史保留供对账
    {
        "key": "caotai-t404-2",
        "name": "双机T404集群（已退役）",
        "domain": "caotai",
        "sort_order": 32,
        "status": "retired",
        "vendor": "nvidia",
        "gpu_model": "NVIDIA T404 16GB",
        "gpus_per_host": 2,
        "hosts": [
            {"key": "ct-t404-1", "name": "退役-01"},
            {"key": "ct-t404-2", "name": "退役-02"},
        ],
        "badges": [
            {"text": localized("已退役", "Retired"),
             "mark": None, "tone": "neutral",
             "tooltip": localized(
                 "机器已搬走，历史数据留着对账",
                 "Hardware removed; historical data kept for reference.")},
        ],
        "note": localized(
            "退役集群：不再采集，但排行榜里的历史卡时还算它。",
            "Collection has stopped, but historical GPU-hours remain in the ranking."),
    },

    # 草台 3/3：待接入。hosts 列出来了但还没权限，网页显示占位卡
    {
        "key": "caotai-huabing-4",
        "name": "4机画饼集群（待接入）",
        "domain": "caotai",
        "sort_order": 33,
        "status": "planned",
        "vendor": "nvidia",
        "gpu_model": "NVIDIA B888 288GB",
        "gpus_per_host": 8,
        "hosts": [
            {"key": "ct-hb-1", "name": "画饼-01"},
            {"key": "ct-hb-2", "name": "画饼-02"},
            {"key": "ct-hb-3", "name": "画饼-03"},
            {"key": "ct-hb-4", "name": "画饼-04"},
        ],
        "badges": [
            {"text": localized("待接入", "Pending"),
             "mark": "…", "tone": "neutral",
             "tooltip": localized(
                 "机器到了，SSH 权限还在走流程",
                 "Hardware is here; access is still being arranged.")},
            {"text": localized("下季度", "Next quarter"),
             "mark": None, "tone": "cyan",
             "tooltip": localized(
                 "口头承诺，日期以邮件为准",
                 "Tentatively next quarter; check the email for the final date.")},
        ],
        "note": localized(
            "planned：占位卡场景 —— 有 hosts、无采集数据。",
            "Planned placeholder: hosts are listed, but there's no telemetry yet."),
    },
]

# ---------------------------------------------------------------------------
# 用户。name 必须是能真的出现在 ps 输出里的 Linux 用户名（ASCII，拼音梗可以），
# 中文名进 sample_proc 会把排行榜和进程列表一起搞坏。
#
# weight 是总卡时的相对占比，不是百分比 —— 造数脚本自己归一化。
# 刻意做成长尾：头部几个占掉大半，尾巴一堆 0.2 的过客，这样排行榜的
# 「前 N 名 + 其他」折叠和横条最小宽度才有东西可测。
#
# style 决定造数脚本编什么形状的曲线：
#   trainer  长时间高利用率，正常干活的
#   squatter 显存占着、利用率贴 0 —— 空占检测的正样本，演示站的重点戏
#   burster  短时间打满然后消失，调参/debug 的形状
#   tourist  偶尔冒个头，几十分钟就走
# ---------------------------------------------------------------------------
USERS: list[dict] = [
    # 头部重度用户
    {"name": "laoban-wang", "weight": 9.0, "style": "trainer"},
    {"name": "juanwang-zhao", "weight": 8.5, "style": "trainer"},
    {"name": "tongxiao-liu", "weight": 7.0, "style": "trainer"},
    {"name": "dachuang-chen", "weight": 6.5, "style": "trainer"},
    {"name": "paperdog", "weight": 6.0, "style": "trainer"},
    # 空占大户 —— 演示「显存打满、利用率 0」
    {"name": "zhankeng-xia", "weight": 7.5, "style": "squatter"},
    {"name": "kongzhan-zhu", "weight": 6.8, "style": "squatter"},
    {"name": "jupyter_wangzhe", "weight": 5.5, "style": "squatter"},
    {"name": "tmux-yongjiu", "weight": 4.5, "style": "squatter"},
    {"name": "wangle-guan", "weight": 3.6, "style": "squatter"},
    {"name": "shuijiao_le", "weight": 2.8, "style": "squatter"},
    # 中量 trainer
    {"name": "tiaocan_li", "weight": 4.2, "style": "trainer"},
    {"name": "wanye-sun", "weight": 3.9, "style": "trainer"},
    {"name": "duiqi-hu", "weight": 3.4, "style": "trainer"},
    {"name": "xiaoshi-yang", "weight": 3.1, "style": "trainer"},
    {"name": "lianhe-xu", "weight": 2.7, "style": "trainer"},
    {"name": "ganhuo-ma", "weight": 2.4, "style": "trainer"},
    # burster：短时高峰
    {"name": "tiaocanxia", "weight": 3.3, "style": "burster"},
    {"name": "debug-daren", "weight": 2.9, "style": "burster"},
    {"name": "shenjing-qin", "weight": 2.5, "style": "burster"},
    {"name": "yijian-pao", "weight": 2.2, "style": "burster"},
    {"name": "banye-shang", "weight": 1.9, "style": "burster"},
    {"name": "oom_zhuanjia", "weight": 1.6, "style": "burster"},
    {"name": "chongshi-fan", "weight": 1.3, "style": "burster"},
    {"name": "zuihou-yici", "weight": 1.1, "style": "burster"},
    # tourist：打卡型
    {"name": "shiyanshi-mao", "weight": 0.9, "style": "tourist"},
    {"name": "shixi-sheng", "weight": 0.8, "style": "tourist"},
    {"name": "xinlai-de", "weight": 0.7, "style": "tourist"},
    {"name": "guolu-ke", "weight": 0.6, "style": "tourist"},
    {"name": "mobai-gpu", "weight": 0.5, "style": "tourist"},
    {"name": "zhishi-kankan", "weight": 0.45, "style": "tourist"},
    {"name": "cesun-yixia", "weight": 0.4, "style": "tourist"},
    {"name": "biyesheng-99", "weight": 0.35, "style": "tourist"},
    {"name": "daoshi-pai-de", "weight": 0.3, "style": "tourist"},
    {"name": "yunwei_laoli", "weight": 0.25, "style": "tourist"},
    {"name": "root-daibiao", "weight": 0.2, "style": "tourist"},
]

# ---------------------------------------------------------------------------
# 进程名。要像真的从 ps 里抄出来的：一堆 v2/v7/final/final2 的版本号考古现场。
# 长短混着放，长名字用来验证进程列表列宽和 tooltip 截断。
# ---------------------------------------------------------------------------
PROC_NAMES: list[str] = [
    "train.py",
    "train_final.py",
    "train_final_v2.py",
    "train_final_v7.py",
    "train_final_final.py",
    "train_final_donotdelete.py",
    "finetune_lora.py",
    "pretrain_stage2.py",
    "eval_only.py",
    "eval_but_it_is_training.py",
    "sweep_lr_1e-5.py",
    "ablation_no_norm.py",
    "definitely_not_mining",
    "temp_test.py",
    "temp_test_copy.py",
    "temp_test_copy_copy.py",
    "jupyter-lab",
    "ipykernel_launcher.py",
    "vscode-server",
    "tensorboard",
    "sleep_infinity.sh",
    "keep_gpu_warm.sh",
    "hold_my_vram.py",
    "python",
    "python3",
    "bash",
    "torchrun",
    "deepspeed",
    "accelerate_launch.py",
    "run_all_night.sh",
    "wenwen_shifou_paowan.py",
    "dont_kill_this_please.py",
    "benchmark_matmul.py",
    "dataloader_stress.py",
    "resume_from_ckpt_88000.py",
]

# ---------------------------------------------------------------------------
# SMALL：默认演示规模（2 域 / 3 集群 / 6 机 / 48 卡）。
#
# 用 key 从大集合里筛，而不是另抄一份 dict —— 抄一份的话改了大集合的集群名，
# SMALL 里还是老名字，两套演示数据会对不上。
#
# 挑这三个集群的理由：既要小，又要每个特性都留一份样本 ——
#   祖传集群(3机×8=24)   多机 + 显存小，空占演示的舞台
#   H250S(2机×8=16)      跨域第二个域，验证配色不只一种
#   MI999(1机×8=8)       AMD/ROCm 分支不能因为缩规模就丢
# 合计 6 机 48 卡。retired / planned 不进 SMALL：默认演示别一上来就是占位卡。
#
# 注意：筛出来的是同一批 dict 对象的引用，不是深拷贝。消费方（造数脚本）若要
# 往集群 dict 上挂中间状态，请自己 copy.deepcopy，否则会顺手改到大集合。
# ---------------------------------------------------------------------------
SMALL_DOMAIN_KEYS = ("yinshan", "longguo-dianxin")
SMALL_CLUSTER_KEYS = ("yinshan-zuchuan-3", "longguo-h250s-2", "longguo-mi999-1")


def _pick(items: list[dict], keys: tuple[str, ...]) -> list[dict]:
    """按 key 白名单筛子集，顺序沿用大集合（即 sort_order 的相对次序）。"""
    wanted = set(keys)
    return [it for it in items if it["key"] in wanted]


SMALL: dict = {
    "domains": _pick(DOMAINS, SMALL_DOMAIN_KEYS),
    "clusters": _pick(CLUSTERS, SMALL_CLUSTER_KEYS),
}


# ---------------------------------------------------------------------------
# 自检
# ---------------------------------------------------------------------------
def gpu_total(clusters: list[dict]) -> int:
    """一组集群的卡数合计 = Σ 主机数 × 每机卡数。"""
    return sum(len(c["hosts"]) * c["gpus_per_host"] for c in clusters)


def host_total(clusters: list[dict]) -> int:
    return sum(len(c["hosts"]) for c in clusters)


def validate() -> None:
    """把所有不变量断言一遍。改完数据请跑 `python scripts/demo_fixtures.py`。

    这里不是防外部输入，是防手改数据时的低级错误：复制粘贴忘改 key、
    加了主机忘调卡数、tone 拼错。这些错在造数阶段炸掉，比到网页上
    看见幽灵主机再回头查便宜得多。
    """
    # --- 算力域 ---
    dom_keys = [d["key"] for d in DOMAINS]
    assert len(dom_keys) == len(set(dom_keys)), f"算力域 key 重复: {dom_keys}"

    def check_localized_text(value, where: str) -> None:
        """demo 的映射固定为中英双语，且中文排第一以覆盖顺序回退。"""
        if isinstance(value, str):
            assert value, f"{where} 不能为空"
            return
        assert isinstance(value, dict) and value, f"{where} 应为字符串或翻译映射"
        assert tuple(value) == ("zh", "en"), f"{where} 应按 zh/en 排列"
        assert all(isinstance(text, str) and text for text in value.values()), (
            f"{where} 的翻译不能为空")

    # --- 标签库：key 唯一、字段合法 ---
    lib_keys: set[str] = set()
    for b in BADGE_LIBRARY:
        assert b["key"] not in lib_keys, f"标签库 key 重复: {b['key']}"
        lib_keys.add(b["key"])
        assert re.fullmatch(r"[a-z][a-z0-9-]*", b["key"]), f"标签 key 非法: {b['key']}"
        check_localized_text(b["text"], f"标签 {b['key']} text")
        assert b["tone"] in TONES, f"标签 {b['key']} tone 非法: {b['tone']}"
        assert b["mark"] is None or isinstance(b["mark"], str)
        if b["tooltip"] is not None:
            check_localized_text(b["tooltip"], f"标签 {b['key']} tooltip")

    def check_badges(items, where: str) -> None:
        """badges 每项要么是库里的 key，要么是内联的完整定义。"""
        for it in items:
            if isinstance(it, str):
                assert it in lib_keys, f"{where} 引用了不存在的标签 {it}"
                continue
            check_localized_text(it["text"], f"{where} 内联标签 text")
            assert it["tone"] in TONES, f"{where} 内联标签 tone 非法: {it['tone']}"
            assert it.get("mark") is None or isinstance(it["mark"], str)
            if it.get("tooltip") is not None:
                check_localized_text(it["tooltip"], f"{where} 内联标签 tooltip")

    for d in DOMAINS:
        assert re.fullmatch(r"[a-z][a-z0-9-]*", d["key"]), f"域 key 非法: {d['key']}"
        assert d["palette"] in PALETTES, f"域 {d['key']} 的 palette 非法: {d['palette']}"
        assert d["name"], f"域 {d['key']} 缺 name"
        assert isinstance(d["sort_order"], int), f"域 {d['key']} 的 sort_order 应为 int"
        if d["description"] is not None:
            check_localized_text(d["description"], f"域 {d['key']} description")
        check_badges(d.get("badges", []), f"域 {d['key']}")

    # --- 集群 + 主机（主机 key 要求全局唯一，不只是集群内唯一）---
    cl_keys: set[str] = set()
    host_keys: set[str] = set()
    for c in CLUSTERS:
        assert c["key"] not in cl_keys, f"集群 key 重复: {c['key']}"
        cl_keys.add(c["key"])
        assert re.fullmatch(r"[a-z0-9][a-z0-9-]*", c["key"]), f"集群 key 非法: {c['key']}"
        assert c["domain"] in dom_keys, f"集群 {c['key']} 引用了不存在的域 {c['domain']}"
        assert c["status"] in STATUSES, f"集群 {c['key']} status 非法: {c['status']}"
        assert c["vendor"] in VENDORS, f"集群 {c['key']} vendor 非法: {c['vendor']}"
        assert c["gpus_per_host"] > 0, f"集群 {c['key']} 每机卡数须为正"
        assert isinstance(c["sort_order"], int)
        assert c["gpu_model"], f"集群 {c['key']} 缺 gpu_model"
        if c["note"] is not None:
            check_localized_text(c["note"], f"集群 {c['key']} note")
        for h in c["hosts"]:
            assert h["key"] not in host_keys, f"主机 key 全局重复: {h['key']}"
            host_keys.add(h["key"])
            assert re.fullmatch(r"[a-z0-9][a-z0-9-]*", h["key"]), f"主机 key 非法: {h['key']}"
            assert h["name"], f"主机 {h['key']} 缺 name"
        check_badges(c["badges"], f"集群 {c['key']}")

    # --- 卡数总量：两个规模都必须精确命中 ---
    assert gpu_total(CLUSTERS) == LARGE_GPUS, \
        f"大集合卡数应为 {LARGE_GPUS}，实际 {gpu_total(CLUSTERS)}"
    assert gpu_total(SMALL["clusters"]) == SMALL_GPUS, \
        f"SMALL 卡数应为 {SMALL_GPUS}，实际 {gpu_total(SMALL['clusters'])}"

    # --- SMALL 必须是大集合的真子集，且域引用自洽 ---
    small_dom_keys = {d["key"] for d in SMALL["domains"]}
    assert len(SMALL["domains"]) == len(SMALL_DOMAIN_KEYS), "SMALL 有域 key 没筛到"
    assert len(SMALL["clusters"]) == len(SMALL_CLUSTER_KEYS), "SMALL 有集群 key 没筛到"
    for c in SMALL["clusters"]:
        assert c["domain"] in small_dom_keys, \
            f"SMALL 集群 {c['key']} 的域 {c['domain']} 没被一起筛进来"

    # --- 覆盖度：这些边界分支是演示站要展示的重点，缺一个就没得看 ---
    assert any(c["status"] == "planned" for c in CLUSTERS), "缺 planned 集群（占位卡场景）"
    assert any(c["status"] == "retired" for c in CLUSTERS), "缺 retired 集群"
    assert any(c["vendor"] == "amd" for c in CLUSTERS), "缺 AMD 集群（ROCm 分支）"
    assert any(len(c["badges"]) > 3 for c in CLUSTERS), "缺 >3 枚标签的集群（+N 折叠）"
    assert any(not c["badges"] for c in CLUSTERS), "缺 0 标签集群（无标签排版）"

    # --- 标签库覆盖度：复用是这功能的重点，演示站上要看得见 ---
    assert any(d.get("badges") for d in DOMAINS), "缺挂标签的算力域"
    refs = ([k for d in DOMAINS for k in d.get("badges", []) if isinstance(k, str)]
            + [k for c in CLUSTERS for k in c["badges"] if isinstance(k, str)])
    assert any(refs.count(k) > 1 for k in set(refs)), "缺被多处引用的标签（复用是重点）"
    assert any(any(isinstance(k, str) for k in c["badges"])
               and any(not isinstance(k, str) for k in c["badges"])
               for c in CLUSTERS), "缺「库引用 + 内联」混用的集群"
    unused = lib_keys - set(refs)
    assert not unused, f"标签库里有没被引用的条目: {sorted(unused)}"

    # --- 用户 ---
    names = [u["name"] for u in USERS]
    assert len(names) == len(set(names)), "用户名重复"
    assert 30 <= len(names) <= 40, f"用户数应在 30-40，实际 {len(names)}"
    for u in USERS:
        assert USERNAME_RE.fullmatch(u["name"]), f"用户名不符合 Linux 规范: {u['name']}"
        assert u["weight"] > 0, f"用户 {u['name']} 权重须为正"
        assert u["style"] in STYLES, f"用户 {u['name']} style 非法: {u['style']}"
    for s in STYLES:
        assert any(u["style"] == s for u in USERS), f"没有任何 {s} 类型用户"

    # --- 进程名：ASCII，且不带路径分隔符（ps 里取的是 comm/短名）---
    assert len(PROC_NAMES) == len(set(PROC_NAMES)), "进程名重复"
    for p in PROC_NAMES:
        assert p.isascii() and p.strip() == p and p, f"进程名非法: {p!r}"
        assert "/" not in p, f"进程名不应带路径: {p!r}"


def _summary_rows() -> list[tuple[str, str, str, str, str]]:
    """两种规模各一行：域数 / 集群数 / 主机数 / 卡数 / 用户数。"""
    return [
        ("large", str(len(DOMAINS)), str(len(CLUSTERS)),
         str(host_total(CLUSTERS)), str(gpu_total(CLUSTERS))),
        ("SMALL", str(len(SMALL["domains"])), str(len(SMALL["clusters"])),
         str(host_total(SMALL["clusters"])), str(gpu_total(SMALL["clusters"]))),
    ]


def _print_summary() -> None:
    header = ("scale", "domains", "clusters", "hosts", "GPUs")
    rows = _summary_rows()
    widths = [max(len(r[i]) for r in (header, *rows)) for i in range(len(header))]
    line = "  ".join("-" * w for w in widths)

    print("  ".join(h.ljust(w) for h, w in zip(header, widths)))
    print(line)
    for r in rows:
        # 数字列右对齐，方便肉眼核 256 / 48
        print("  ".join(
            v.ljust(w) if i == 0 else v.rjust(w)
            for i, (v, w) in enumerate(zip(r, widths))
        ))
    print(line)
    print(f"users: {len(USERS)}   proc_names: {len(PROC_NAMES)}")

    # 每个域挂了几个集群 / 多少卡 —— 分布故意不均，这里打出来好确认
    print("\n算力域分布（刻意不均匀）:")
    for d in DOMAINS:
        owned = [c for c in CLUSTERS if c["domain"] == d["key"]]
        print(f"  {d['name']:<12} palette={d['palette']:<7} "
              f"clusters={len(owned)}  hosts={host_total(owned):>2}  "
              f"GPUs={gpu_total(owned):>3}")

    print("\n集群明细:")
    for c in CLUSTERS:
        flag = "" if c["status"] == "active" else f"  [{c['status']}]"
        print(f"  {c['name']:<22} {len(c['hosts']):>2}机 × {c['gpus_per_host']:>2}卡 "
              f"= {len(c['hosts']) * c['gpus_per_host']:>3}  "
              f"badges={len(c['badges'])}  {c['gpu_model']}{flag}")


if __name__ == "__main__":
    validate()
    print("validate() OK —— 所有不变量通过\n")
    _print_summary()
