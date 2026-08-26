# 部署指南

简体中文 | [English](DEPLOYMENT.en.md) | [文档目录](README.md) | [项目首页](../README.md)

把 cluster-gpu-monitor 装到一台常开的机器上（下称 **监控机**），它通过 SSH 轮询各 GPU 节点，
自己跑一个网页服务给团队看。目标节点上**不装任何东西**，也不需要 root。

本文讲 Python 虚拟环境、systemd 和不可变 release 的原生部署。需要容器部署时改读
[Docker Compose 指南](DOCKER.md)；两种方式任选其一，不要同时运行两个 collector。

第一次试用请先走 [README 快速开始](../README.md#快速开始)。本文是完整生产手册；字段解释见
[配置参考](CONFIGURATION.md)，数据与安全边界见[架构与设计取舍](ARCHITECTURE.md)。

本文占位符，按你的环境替换：

| 占位符 | 含义 |
| --- | --- |
| `<SERVER_IP>` | 监控机的 IP（内网或公网） |
| `<YOUR_DOMAIN>` | 你的域名，例如 `gpu.example.com` |
| `<ROOT>` | 代码目录，示例用 `/opt/gpu-monitor` |
| `<USER>` | 跑采集器和备份的系统账户，示例用 `gpumon`，持有 SSH 配置和数据库写权限 |
| `<WEB_USER>` | 只跑 Web 的无登录账户，示例用 `gpumon-web`，只能读配置和数据库 |
| `<BASTION>` | 跳板机的 SSH 别名 |
| `<YOUR_SUBNET>` | 允许访问的内网段，例如 `10.10.0.0` |

---

## 0. 三条访问路径，先选一条

三种都支持，按你有什么条件选：

| 路径 | 适用场景 | 加密 | 复杂度 |
| --- | --- | --- | --- |
| **1. IP + HTTP 直连** | 内网、试用、只有你自己看 | 无（明文） | 一条命令 |
| **2. 域名 + Caddy 自动 HTTPS** | 生产推荐 | 可信证书，绿锁 | 两行配置 |
| **3. 无域名 → DuckDNS + DNS-01** | 没域名，或入站 80/443 被封 | 可信证书，绿锁 | 需带插件的 Caddy |

第 1～4 节是所有路径共用的准备工作，做完再跳到第 5 节挑你的路径。

---

## 1. 前置条件

监控机：

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)（装依赖 / 建虚拟环境）
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
  ```
- 到**每一台**目标 GPU 节点的 SSH 免密访问（密钥认证）
- 系统自带的 `ssh` 命令（采集器直接调它，不用 paramiko，这样才能复用 `~/.ssh/config`）

目标 GPU 节点：

- **什么都不用装。** 没有 agent、没有 daemon、不写文件。采集脚本经 `ssh <alias> bash -s`
  从 stdin 喂进去，在远端内存里跑完就没了。
- 普通账户就够，**不需要 root**。只要该账户能跑 `nvidia-smi`（或 `rocm-smi` / `amd-smi`）
  和 `ps`，能读 `/proc/stat`、`/proc/meminfo` —— 这些默认都对普通用户开放。
- 需要 `bash` 和 coreutils，基本等于「是台 Linux」。

---

## 2. SSH 配置：整套部署的地基

设计上代码里**不出现任何 IP、端口、密钥路径**。`inventory.yaml` 里只写 SSH 别名，
真实网络拓扑全在 `~/.ssh/config` 里。这一层间接带来两个好处，后面会用到。

先建一把专用密钥（别拿你的个人 key 去跑服务）：

```bash
ssh-keygen -t ed25519 -N '' -f ~/.ssh/id_ed25519_gpumon -C 'gpumon@monitor-host'
cat ~/.ssh/id_ed25519_gpumon.pub   # 分发这把公钥
```

把公钥追加到每台目标节点的 `~/.ssh/authorized_keys`（`ssh-copy-id` 最省事）：

```bash
ssh-copy-id -i ~/.ssh/id_ed25519_gpumon.pub <user>@<node-addr>
```

然后写 `~/.ssh/config`：

```sshconfig
# 全局默认
Host *
    IdentityFile ~/.ssh/id_ed25519_gpumon
    ServerAliveInterval 15
    ServerAliveCountMax 3

# --- 直连节点（同机房 / 有路由可达）---
Host node-a1
    HostName <NODE_A1_ADDR>
    User <REMOTE_USER>

Host node-a2
    HostName <NODE_A2_ADDR>
    User <REMOTE_USER>

# --- 跳板机本身 ---
Host <BASTION>
    HostName <BASTION_ADDR>
    User <BASTION_USER>
    Port 22

# --- 跳板机后面的节点：ProxyJump 一行搞定 ---
# ssh 先连 <BASTION>，再从跳板机内部连到 node-b1，全程一条命令、一次认证链。
Host node-b1
    HostName <NODE_B1_INTERNAL_ADDR>
    User <REMOTE_USER>
    ProxyJump <BASTION>

# 多级跳板就逗号串联：ProxyJump <BASTION>,<BASTION2>
```

> 跳板机上也要有这把公钥（`authorized_keys`）才能中转。ProxyJump 只是转发 TCP，
> 采集脚本仍在最终节点上执行，跳板机不需要有 GPU、也不需要装东西。

**验证每台都能采到**，这一步不过就别往下走：

```bash
for a in node-a1 node-a2 node-b1; do
  printf '%-12s ' "$a"
  ssh -o BatchMode=yes -o ConnectTimeout=10 "$a" 'nvidia-smi -L | head -1' || echo FAIL
done
```

每行都回 `GPU 0: NVIDIA ...` 才算通。`BatchMode=yes` 很关键：它禁掉一切交互提示，
能问密码就说明密钥没配好，服务化之后会静默卡死。

采集器不会替你改写 `StrictHostKeyChecking`。能从资产方核验指纹时，先人工确认并写入
`known_hosts`，再在该 alias 下设 `StrictHostKeyChecking yes`；若外部资产确实无法核验，
可以只在对应 alias 显式保留 `StrictHostKeyChecking accept-new`。不要把宽松策略写成
所有主机的全局默认。

**为什么这层间接值得**：

1. **迁移监控机只需重写 ssh config。** `inventory.yaml` 里的 `key` 是历史数据的稳定锚点，
   换机器时 `ssh_alias` 背后的 IP/跳板怎么变都无所谓，只要 `key` 不动，
   历史曲线和统计就是连续的 —— 数据库按 `key` 关联，不按地址。
2. **节点换 IP、加跳板、走代理，都不用改代码，也不用重建库。** 改 ssh config 即可。

---

## 3. 按 release 布局安装

生产环境不要把 git checkout、`.venv`、真实配置和数据库平铺在同一目录，也不要用
`rsync --delete` 原地覆盖正在运行的代码。推荐布局：

```text
<ROOT>/releases/<commit>/   # 该 commit 的源码及在本机新建的 .venv
<ROOT>/current -> releases/<commit>
<ROOT>/previous -> releases/<old-commit>
<ROOT>/config/              # inventory.yaml / settings.toml，不随 release 切换
<ROOT>/data/                # SQLite 与 backups/，不随 release 切换
```

首次安装可按下面方式从一个干净 checkout 建 release；真实配置只复制到独立目录：

```bash
SRC=<CLEAN_CHECKOUT>
ROOT=<ROOT>
APP_USER=<USER>
APP_GROUP=$(id -gn "$APP_USER")
COMMIT=$(git -C "$SRC" rev-parse HEAD)

sudo install -d -o root -g root "$ROOT/releases" "$ROOT/releases/$COMMIT"
sudo install -d -m 0750 -o root -g "$APP_GROUP" "$ROOT/config"
sudo install -d -m 0750 -o "$APP_USER" -g "$APP_GROUP" "$ROOT/data"
git -C "$SRC" archive "$COMMIT" \
  | sudo tar --no-same-owner -x -C "$ROOT/releases/$COMMIT"
sudo chown -R root:"$APP_GROUP" "$ROOT/releases/$COMMIT"
sudo chmod -R u=rwX,g=rX,o= "$ROOT/releases/$COMMIT"
sudo chmod -R a-w "$ROOT/releases/$COMMIT"
sudo install -d -m 0700 -o "$APP_USER" -g "$APP_GROUP" "$ROOT/releases/$COMMIT/.venv"
sudo -u "$APP_USER" uv venv --allow-existing "$ROOT/releases/$COMMIT/.venv"
sudo -u "$APP_USER" env UV_PROJECT_ENVIRONMENT="$ROOT/releases/$COMMIT/.venv" \
  uv sync --project "$ROOT/releases/$COMMIT" --frozen --no-dev
sudo chown -R root:"$APP_GROUP" "$ROOT/releases/$COMMIT"
sudo chmod -R u=rwX,g=rX,o= "$ROOT/releases/$COMMIT"
sudo chmod -R a-w "$ROOT/releases/$COMMIT"

sudo cp -n "$ROOT/releases/$COMMIT/config/inventory.example.yaml" "$ROOT/config/inventory.yaml"
sudo cp -n "$ROOT/releases/$COMMIT/config/settings.example.toml" "$ROOT/config/settings.toml"
sudo chown "root:$APP_GROUP" "$ROOT/config/inventory.yaml" "$ROOT/config/settings.toml"
sudo chmod 0640 "$ROOT/config/inventory.yaml" "$ROOT/config/settings.toml"
# 现在编辑两份真实配置；ssh_alias 必须与服务账户 ~/.ssh/config 完全一致。

sudo ln -s "releases/$COMMIT" "$ROOT/current"
sudo -u "$APP_USER" env GPUMON_ROOT="$ROOT" \
  "$ROOT/current/.venv/bin/gpumon" config-check
sudo -u "$APP_USER" env GPUMON_ROOT="$ROOT" \
  "$ROOT/current/.venv/bin/gpumon" initdb
sudo -u "$APP_USER" env GPUMON_ROOT="$ROOT" \
  "$ROOT/current/.venv/bin/gpumon" collect --once
```

后续升级也要先在 `releases/.staging-<commit>.*` 构建，依次完成严格配置校验、旁路 Web
健康检查和 SQLite 在线备份；然后用“新建临时软链接 + `mv -T`”原子替换 `current`。
先重启 collector 并确认新样本时间推进，再重启 web；失败时把 `current` 指回
`previous` 并重启即可。不要从开发机同步 `.venv`，更不要把 `config/` 或 `data/`
复制进 release。构建完成的 release 及其父目录应由 root 持有并保持只读，运行服务只能读取。

---

## 4. 装成 systemd 服务

系统级 unit 都从 `<ROOT>/current` 执行代码，同时把 `GPUMON_ROOT` 指向稳定的
`<ROOT>`。采集器与 Web 必须使用不同账户：Web 不持有 SSH home/key，代码会用 SQLite
`mode=ro` + `query_only` 强制只读，systemd 也把整个应用根挂成只读，并为 Web 设置
256/384 MiB 内存水位/硬上限和 64 个任务上限。备份 timer 是唯一
自动调度源，每天 04:00 触发一次：

| 文件 | 类型 | 说明 |
| --- | --- | --- |
| `system-gpumon-collector.service` | 系统级 | 采集器，跟随 `current` |
| `system-gpumon-web.service` | 系统级 | 独立无登录账户运行的只读 Web，跟随 `current` |
| `gpumon-backup.service` | 系统级 oneshot | 原子 SQLite 备份，不单独 enable |
| `gpumon-backup.timer` | 系统级 timer | 每日 04:00 唯一触发源 |
| `gpumon-collector.service` / `gpumon-web.service` | 用户级 | 开发机平铺 checkout 使用 |

**系统级（服务器部署用这个）**：

```bash
ROOT=<ROOT>
APP_USER=<USER>
WEB_USER=<WEB_USER>
APP_GROUP=$(id -gn "$APP_USER")

# Web 账户没有可登录 shell、home 或 SSH key，只通过共享组读取运行所需文件。
id -u "$WEB_USER" >/dev/null 2>&1 || \
  sudo useradd --system --user-group --no-create-home \
    --home-dir /nonexistent --shell /usr/sbin/nologin "$WEB_USER"
sudo usermod -a -G "$APP_GROUP" "$WEB_USER"
sudo chmod 0700 "$(getent passwd "$APP_USER" | cut -d: -f6)"
sudo chown root:"$APP_GROUP" "$ROOT/config"
sudo chown "$APP_USER:$APP_GROUP" "$ROOT/data"
sudo chmod 0750 "$ROOT/config" "$ROOT/data"
sudo find "$ROOT/config" -maxdepth 1 -type f -exec chmod 0640 {} +
sudo find "$ROOT/data" -maxdepth 1 -type f -name 'gpumon.db*' \
  -exec chown "$APP_USER:$APP_GROUP" {} + -exec chmod 0640 {} +

sed "s#__ROOT__#$ROOT#g; s#__USER__#$APP_USER#g; s#__GROUP__#$APP_GROUP#g" \
  "$ROOT/current/deploy/systemd/system-gpumon-collector.service" \
  | sudo tee /etc/systemd/system/gpumon-collector.service >/dev/null
sed "s#__ROOT__#$ROOT#g; s#__WEB_USER__#$WEB_USER#g; s#__GROUP__#$APP_GROUP#g" \
  "$ROOT/current/deploy/systemd/system-gpumon-web.service" \
  | sudo tee /etc/systemd/system/gpumon-web.service >/dev/null
sed "s#__ROOT__#$ROOT#g; s#__USER__#$APP_USER#g; s#__GROUP__#$APP_GROUP#g" \
  "$ROOT/current/deploy/systemd/gpumon-backup.service" \
  | sudo tee /etc/systemd/system/gpumon-backup.service >/dev/null
sudo cp "$ROOT/current/deploy/systemd/gpumon-backup.timer" \
  /etc/systemd/system/gpumon-backup.timer
sudo systemd-analyze verify /etc/systemd/system/gpumon-{collector,web,backup}.service \
  /etc/systemd/system/gpumon-backup.timer
sudo systemctl daemon-reload
sudo systemctl enable --now gpumon-collector gpumon-web gpumon-backup.timer
```

**用户级（自己机器上试用）**使用源码 checkout 的 `.venv`，并显式区分代码根和
配置/数据根：

```bash
CODE_ROOT=<CLEAN_CHECKOUT>
STATE_ROOT=<STATE_ROOT>
mkdir -p ~/.config/systemd/user
for u in collector web; do
  sed "s#__CODE_ROOT__#$CODE_ROOT#g; s#__STATE_ROOT__#$STATE_ROOT#g" \
    "$CODE_ROOT/deploy/systemd/gpumon-$u.service" \
    > ~/.config/systemd/user/gpumon-$u.service
done
systemctl --user daemon-reload
systemctl --user enable --now gpumon-collector gpumon-web
sudo loginctl enable-linger "$USER"  # 需要注销后继续运行时才开
```

**不要同时启用系统级和用户级采集器**，否则两个进程会争写同一 SQLite。配置与数据
按 `GPUMON_ROOT` 解析；Web 静态资源始终从当前代码 release 读取，二者有意分离。

---

## 5. 路径 1：IP + HTTP 直连（最简）

最快看到界面的办法。改 `config/settings.toml`：

```toml
[web]
host = "0.0.0.0"
port = 8848
```

或者临时命令行覆盖：

```bash
uv run gpumon web --host 0.0.0.0 --port 8848
```

浏览器打开 `http://<SERVER_IP>:8848`。

> **警告：明文传输。**
>
> 这是**纯 HTTP，没有加密，也没有应用内认证**。页面内容（谁在用哪张卡）会明文传输。
>
> **只在隔离且可信的网络里这么用**（实验室内网、办公局域网、公司 VPN 之内），并用
> 防火墙或安全组限制来源。
>
> 另外，`--host 0.0.0.0` 意味着**凡是能连到这个端口的人都能访问**，没有网络层过滤。
> 当前 Web 没有内置登录，所以这条路径完全依赖网络隔离。必须靠防火墙收窄来源：
>
> ```bash
> # 只放行某个内网段访问 8848（示例，按你的网段改）
> sudo ufw allow from <YOUR_SUBNET>/24 to any port 8848 proto tcp
> ```
>
> 只要这台机器有公网 IP，就**不要**用这条路径对外开放，走路径 2 或 3。

只想自己看、不想开任何端口？SSH 端口转发最干净，后端保持 `127.0.0.1`：

```bash
# 在你的笔记本上执行，然后访问 http://127.0.0.1:8848
ssh -N -L 8848:127.0.0.1:8848 <monitor-host>
```

---

## 6. 路径 2：域名 + Caddy 自动 HTTPS（生产推荐）

后端**回到** `127.0.0.1`，只由 Caddy 对外，TLS 和鉴权都在 Caddy 做。

```toml
# config/settings.toml
[web]
host = "127.0.0.1"
port = 8848
```

### 6.1 DNS

把 `<YOUR_DOMAIN>` 的 A 记录指到监控机公网 IP，等生效：

```bash
dig +short <YOUR_DOMAIN>
```

### 6.2 装 Caddy

```bash
# Debian / Ubuntu 官方源
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
  | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
  | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install -y caddy
```

### 6.3 口令 hash 走环境变量

```bash
caddy hash-password                              # 按隐藏提示输入并确认，输出 $2a$14$...

sudo mkdir -p /etc/gpumon
sudo tee /etc/gpumon/caddy.env >/dev/null <<'EOF'
GPUMON_BASIC_HASH='<粘贴上面的 hash>'
EOF
sudo chmod 600 /etc/gpumon/caddy.env
```

`GPUMON_BASIC_HASH` **必须用单引号包起来**，bcrypt hash 里有 `$`，不加引号会被 shell
当变量展开，结果是个残缺 hash，症状是「口令怎么输都不对」。

让 Caddy 读这个文件：

```bash
sudo systemctl edit caddy      # 写入下面三行
# [Service]
# EnvironmentFile=/etc/gpumon/caddy.env
```

### 6.4 Caddyfile

完整模板把浏览器安全头收在一个可复用片段里。`style-src` 保留 `'unsafe-inline'` 是为了兼容
ECharts tooltip 和现有组件生成的行内样式；脚本仍严格限制为同源，不允许 inline/eval：

```caddyfile
(gpumon_security_headers) {
	header {
		Content-Security-Policy "default-src 'self'; base-uri 'none'; connect-src 'self'; font-src 'self'; form-action 'self'; frame-ancestors 'none'; frame-src 'none'; img-src 'self' data:; object-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'"
		X-Content-Type-Options "nosniff"
		Referrer-Policy "no-referrer"
		Permissions-Policy "accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()"
		X-Frame-Options "DENY"
	}
	@gpumon_no_store path / /index.html /api/*
	header @gpumon_no_store Cache-Control "no-store"
}

<YOUR_DOMAIN> {
	import gpumon_security_headers
	header Strict-Transport-Security "max-age=31536000"
	basic_auth {
		team {$GPUMON_BASIC_HASH}
	}
	reverse_proxy 127.0.0.1:8848
	log {
		output file /var/log/caddy/gpumon.log
	}
}
```

完整带注释的模板见 `deploy/caddy/Caddyfile.example`。HSTS 只用于有可信证书的域名入口；
自签 IP 保底入口不要设置，避免浏览器记住一个无法自动信任的证书入口。GitHub Pages 无法
配置这些响应头，因此 `web/index.html` 另带等价的 meta CSP；`frame-ancestors` 仍只能由
正式部署的响应头生效。

> 指令名按版本：Caddy ≥ 2.8 是 `basic_auth`，2.7 及更早是 `basicauth`。
> `caddy version` 确认一下。

```bash
sudo cp deploy/caddy/Caddyfile.example /etc/caddy/Caddyfile
sudo vim /etc/caddy/Caddyfile          # 填 <YOUR_DOMAIN>
sudo bash -c 'set -a; . /etc/gpumon/caddy.env; set +a; caddy validate --adapter caddyfile --config /etc/caddy/Caddyfile'
sudo systemctl enable --now caddy && sudo systemctl restart caddy
```

模板关闭了 Caddy admin API，因此后续更新也必须先 `caddy validate`，再受控 restart。
校验命令只加载环境文件、不回显变量；显式 adapter 也避免 staging 文件名被误当成 JSON。

首次启动 Caddy 会自动向 Let's Encrypt 申请证书并配置自动续期，什么都不用管。
前提是**入站 80 和 443 都可达**：80 用于 HTTP-01 挑战和 HTTP→HTTPS 跳转，443 是正经服务。
云主机记得在安全组放行 80/443，**8848 绝对不要放行**。

验证：

```bash
curl -I https://<YOUR_DOMAIN>/                              # 期望 401（没带凭据）
curl -u 'team:<你的口令>' https://<YOUR_DOMAIN>/api/health   # 期望 {"ok":true,"status":"ok",...}
curl -sSI -u 'team:<你的口令>' https://<YOUR_DOMAIN>/ | grep -Ei \
  'content-security-policy|strict-transport-security|x-content-type-options|cache-control'
```

---

## 7. 路径 3：没有域名？用 DuckDNS + DNS-01

[DuckDNS](https://www.duckdns.org/) 是免费动态 DNS，给你一个
`<YOUR_SUBDOMAIN>.duckdns.org` 子域名。配合 **DNS-01** 挑战，就能拿到浏览器认可的
可信证书 —— **而且不需要任何入站端口可达**。

### 7.1 为什么是 DNS-01（这条最值钱）

ACME 签证书要证明「这域名是你的」，三种挑战方式：

| 挑战 | 证明方式 | 要求 |
| --- | --- | --- |
| HTTP-01 | 在 `:80` 上放一个文件让 CA 来取 | **入站 80 必须可达** |
| TLS-ALPN-01 | 在 `:443` 上做特殊 TLS 握手 | **入站 443 必须可达** |
| **DNS-01** | 在 DNS 里写一条 TXT 记录 | **只要能出站访问 DNS 商 API** |

DNS-01 全程是监控机主动调 DuckDNS 的 HTTP API 写 TXT 记录，CA 去查 DNS，
**没有任何一步需要外部连进你的机器**。

这一条正好救了几类常见困境：

- 云厂商 / 机房 / 运营商**封禁入站 80、443**（家宽、部分地区的合规限制很常见）
- 机器在 NAT 后面，没法做端口映射
- 你根本不想开 80/443，只想开个非标端口

对外用非标端口（如 8443），80/443 封着也无所谓，绿锁照样有。

> 合规提醒：部分地区/国家用域名对外提供 Web 服务有备案或许可要求，
> 未合规的域名在 80/443 上可能被中间设备拦截。这属于本地法规问题，
> 换端口不解决合规，只解决连通性。

### 7.2 注册 DuckDNS

1. 打开 https://www.duckdns.org/ ，用 GitHub / Google 等第三方账号登录
2. 在 `domains` 输入框填一个想要的名字，点 **add domain**，得到 `<YOUR_SUBDOMAIN>.duckdns.org`
3. 页面顶部有一行 **token**，复制它（这就是 API 凭据，等同密码，别泄露）
4. 把子域名指向监控机（浏览器直接访问下面这个 URL 也行，回 `OK` 即成功）：

```bash
curl "https://www.duckdns.org/update?domains=<YOUR_SUBDOMAIN>&token=<TOKEN>&ip=<SERVER_IP>"
# 留空 ip= 则用你当前出网 IP，适合动态 IP：
# curl "https://www.duckdns.org/update?domains=<YOUR_SUBDOMAIN>&token=<TOKEN>&ip="
```

IP 会变的话，加个 cron 定时刷新：

```bash
# crontab -e
*/5 * * * * curl -fsS "https://www.duckdns.org/update?domains=<YOUR_SUBDOMAIN>&token=<TOKEN>&ip=" >/dev/null
```

### 7.3 装带 duckdns 插件的 Caddy

DNS-01 需要 Caddy 能调 DNS 商 API，官方预编译二进制**不含**这些插件，得自己带。三种办法，挑一种：

```bash
# 办法 A：官方下载站按需打包（最省事，不需要 Go）
sudo curl -L -o /usr/local/bin/caddy \
  "https://caddyserver.com/api/download?os=linux&arch=amd64&p=github.com/caddy-dns/duckdns"
sudo chmod +x /usr/local/bin/caddy
/usr/local/bin/caddy version

# 办法 B：xcaddy 自己编（需要 Go 1.22+，可控、可复现）
go install github.com/caddyserver/xcaddy/cmd/xcaddy@latest
xcaddy build --with github.com/caddy-dns/duckdns
sudo install -m755 ./caddy /usr/local/bin/caddy

# 办法 C：已经用 apt 装过官方版 —— 原地加插件（会拉最新版重装二进制）
sudo caddy add-package github.com/caddy-dns/duckdns
sudo systemctl restart caddy
```

不管用哪种，**装完必须确认插件真的在里面**，这一步别省：

```bash
caddy list-modules | grep dns.providers
# 期望看到 dns.providers.duckdns
```

没有输出就是插件没编进去，后面 DNS-01 会一直失败在「找不到 dns provider」。
办法 A/B 装到 `/usr/local/bin/caddy`，而 apt 版的 unit 指向 `/usr/bin/caddy` ——
换了路径记得 `sudo systemctl edit caddy` 改 `ExecStart`，或直接覆盖 `/usr/bin/caddy`。

### 7.4 配置

token 也走环境文件，别写进 Caddyfile：

```bash
sudo tee -a /etc/gpumon/caddy.env >/dev/null <<'EOF'
DUCKDNS_TOKEN='<你的 duckdns token>'
EOF
sudo chmod 600 /etc/gpumon/caddy.env
```

Caddyfile：

```caddyfile
<YOUR_SUBDOMAIN>.duckdns.org:8443 {
	import gpumon_security_headers
	header Strict-Transport-Security "max-age=31536000"
	tls {
		dns duckdns {env.DUCKDNS_TOKEN}
		# 显式指定解析器，绕开本机 DNS 缓存导致的 TXT 校验失败
		resolvers 1.1.1.1 8.8.8.8
	}
	basic_auth {
		team {$GPUMON_BASIC_HASH}
	}
	reverse_proxy 127.0.0.1:8848
	log {
		output file /var/log/caddy/gpumon.log
	}
}
```

```bash
sudo systemctl restart caddy
sudo journalctl -u caddy -f          # 看证书签发过程，通常 10~60 秒
```

访问 `https://<YOUR_SUBDOMAIN>.duckdns.org:8443`。安全组只需放行 8443。

换别的 DNS 商就换插件和指令名，套路完全一样：

| DNS 商 | 插件 | Caddyfile |
| --- | --- | --- |
| Cloudflare | `github.com/caddy-dns/cloudflare` | `dns cloudflare {env.CF_API_TOKEN}` |
| DuckDNS | `github.com/caddy-dns/duckdns` | `dns duckdns {env.DUCKDNS_TOKEN}` |
| 其他 | 见 https://github.com/caddy-dns | 同名指令 |

### 7.5 域名被 SNI 阻断怎么办

极端情况：TCP 能连通、TLS 握手直接被 RST（`curl` 报
`Connection reset by peer` 在握手阶段）。这通常是中间设备按 **SNI**（TLS 握手里
明文携带的域名）做的阻断 —— `duckdns.org` 这类免费动态 DNS 域名在某些线路上就被针对过。

绕法：**加一个 IP 直连入口**。浏览器按 IP 访问时 TLS 握手里**不带 SNI**，
中间设备就没有可匹配的域名。

```caddyfile
# 必须放在文件最前面：无 SNI 的连接默认落到下面这个 IP 站点
{
	default_sni <SERVER_IP>
}

# 域名入口（绿锁）—— 能访问的人走这个
<YOUR_SUBDOMAIN>.duckdns.org:8443 {
	import gpumon_security_headers
	header Strict-Transport-Security "max-age=31536000"
	tls {
		dns duckdns {env.DUCKDNS_TOKEN}
		resolvers 1.1.1.1 8.8.8.8
	}
	basic_auth { team {$GPUMON_BASIC_HASH} }
	reverse_proxy 127.0.0.1:8848
	log { output file /var/log/caddy/gpumon.log }
}

# IP 保底入口（自签，浏览器首次告警点继续即可，流量仍是 TLS 加密）
https://<SERVER_IP>:8443 {
	tls internal
	import gpumon_security_headers
	# 自签 IP 入口不设置 HSTS
	basic_auth { team {$GPUMON_BASIC_HASH} }
	reverse_proxy 127.0.0.1:8848
	log { output file /var/log/caddy/gpumon.log }
}
```

没有 `default_sni` 的话，不带 SNI 的连接 Caddy 找不到匹配站点，会直接拒绝握手 ——
这就是它存在的全部理由。

两个入口可以并存共用同一端口：能正常访问域名的人走绿锁，其余人走 IP 入口。
自签证书虽然有告警，但**链路仍是完整 TLS**，口令不会明文过网，比路径 1 安全得多。

彻底没有可用公网入口时，用 `cloudflared` 之类的出站隧道，或让团队走 SSH 端口转发。

---

## 8. 日常运维

### 改了 inventory.yaml 之后

**加机器**：在对应集群的 `hosts` 下加一条 + 在 `~/.ssh/config` 加别名并分发公钥，然后：

```bash
sudo systemctl restart gpumon-collector      # 采集器只在启动时读 inventory
```

网页会自动出现新机器，零改代码。加之前先验证 SSH 通：

```bash
sudo -u <USER> ssh -o BatchMode=yes -o ConnectTimeout=10 <new-alias> 'nvidia-smi -L'
```

**退役机器**：**不要删条目**。删了 DB 里的历史行还在，网页会挂一堆永久离线的幽灵卡。
给该主机或整个集群标 `status: retired`，然后重启两个服务：

```bash
sudo systemctl restart gpumon-collector gpumon-web
```

采集器随即停止探测（不再累加连接失败），网页彻底隐去该机，DB 行和历史采样保留供对账。

**改了 settings.toml**：重启对应服务（`[collector]` 改了重启 collector，
`[web]`/`[privacy]` 改了重启 web）。

**只改了 `web/` 下的前端文件**：不用重启。静态文件是每次请求现读磁盘的，刷新页面即生效。

### 日志

```bash
# 系统级
sudo journalctl -u gpumon-collector -f            # 每轮采集摘要、失败原因
sudo journalctl -u gpumon-web -f                  # HTTP 访问日志
sudo journalctl -u caddy -f                       # 证书签发、TLS 错误
sudo journalctl -u gpumon-collector --since '1 hour ago' | grep -i fail

# 用户级
journalctl --user -u gpumon-collector -f

# Caddy 访问日志（JSON 行）
sudo tail -f /var/log/caddy/gpumon.log
```

### 健康检查

```bash
curl -fsS http://127.0.0.1:8848/api/live
# {"ok":true,"status":"alive"}
curl -fsS http://127.0.0.1:8848/api/health
# {"ok":true,"status":"ok","last_sample_ts":1234567890,"last_sample_age_s":18,"stale_after_s":120}
```

`/api/live` 是不读取配置/数据库的进程 liveness。`/api/health` 是 readiness：配置或
数据库不可用时返回 HTTP 503；样本超过 `stale_after_s` 时仍返回 HTTP 200，但 JSON 为
`ok=false,status=stale`，所以历史页面仍可查看。`last_sample_age_s` 应当在
`poll_interval_s` 附近波动，持续 stale 说明采集器挂了或全线 SSH 失败。

```bash
curl -fsS http://127.0.0.1:8848/api/collector/status | python3 -m json.tool
```

每台机器一条，看这几个字段：

| 字段 | 含义 |
| --- | --- |
| `online` | 最近 120 秒内成功采过 |
| `gpus_seen` / `gpus_expected` | 实际探到的卡数 / inventory 里写的期望卡数 |
| `consec_fail` | 连续失败次数，0 = 上一轮成功 |
| `last_error` | 最后一次失败原因（SSH 超时、命令不存在等） |
| `last_ok_ts` / `last_try_ts` | 最后成功 / 最后尝试的时间戳 |

一条命令列出所有不健康的机器：

```bash
curl -fsS http://127.0.0.1:8848/api/collector/status \
  | python3 -c 'import json,sys; [print(h["key"], h["gpus_seen"], "/", h["gpus_expected"], h["last_error"]) for h in json.load(sys.stdin)["hosts"] if not h["online"] or h["gpus_seen"] != h["gpus_expected"]]'
```

端到端自检脚本（采一轮 + 聚合 + 打所有接口）：

```bash
./scripts/verify_e2e.sh
```

### 换访问口令

```bash
caddy hash-password                              # 按隐藏提示输入并确认
sudo vim /etc/gpumon/caddy.env       # 更新 GPUMON_BASIC_HASH（记得单引号）
sudo systemctl restart caddy         # 改了 EnvironmentFile 要 restart，reload 不重读
```

### 备份

数据库使用 SQLite WAL。**不要直接 `cp` 正在写入的数据库**；使用项目内置的在线备份命令：

```bash
ROOT=<ROOT>
APP_USER=<USER>
sudo -u "$APP_USER" env GPUMON_ROOT="$ROOT" \
  "$ROOT/current/.venv/bin/gpumon" backup
```

备份写入 `<ROOT>/data/backups/`：先写临时文件，通过 `quick_check`、权限和 fsync 检查后再
原子发布，并按 `[backup] keep_count` 清理旧备份。`backup.enabled=false` 只跳过 timer 的
定时调用，手工命令仍会立即备份。

数据库是单写者模型。做任何离线改库操作前先 `systemctl stop gpumon-collector`，
避免写竞争。

### 迁移到新监控机

历史数据能无缝延续，因为一切按 `inventory.yaml` 的 `key` 关联，与地址无关：

1. 新机器上走完第 1~4 节
2. 在新机器上重建 `~/.ssh/config`（别名保持同名，`HostName`/`ProxyJump` 按新网络位置改）
3. 老机器 `systemctl stop gpumon-collector`，用上面的 backup 命令生成一致性快照
4. 把快照拷到新机器 `data/gpumon.db`
5. 起新机器的服务，确认 `/api/collector/status` 全绿
6. 停用并禁用老机器的服务（`systemctl disable --now`）

---

## 9. 安全清单

- [ ] **后端端口（8848）绝不对公网放行。** 用反代时后端必须留在 `127.0.0.1`
      —— 否则别人绕过 Caddy 直连 8848，鉴权形同虚设。
      ```bash
      ss -tlnp | grep 8848      # 应该只看到 127.0.0.1:8848
      ```
- [ ] **强随机口令。** 这是唯一的一道门，别用 `gpu123`。
      ```bash
      openssl rand -base64 24
      ```
- [ ] **不要走纯 HTTP 上公网。** 路径 1 只用于可信内网，见第 5 节警告。
- [ ] **上 fail2ban 挡爆破。** Basic Auth 没有速率限制，靠 Caddy 日志里的 401 来封：

      ```ini
      # /etc/fail2ban/filter.d/caddy-auth.conf
      [Definition]
      failregex = "remote_ip":"<HOST>".*"status":401
      datepattern = "ts":{EPOCH}
      ```
      ```ini
      # /etc/fail2ban/jail.d/caddy-auth.local
      [caddy-auth]
      enabled  = true
      filter   = caddy-auth
      port     = 8443
      logpath  = /var/log/caddy/gpumon.log
      maxretry = 8
      findtime = 600
      bantime  = 3600
      ```
      ```bash
      sudo systemctl restart fail2ban
      sudo fail2ban-client status caddy-auth
      ```
      `port` 要和你实际对外的端口一致（路径 2 是 `http,https`，路径 3 是 `8443`）。
- [ ] **专用 SSH 密钥，别复用个人 key。** 目标节点上用普通账户，不给 sudo。
      需要更严的话，在目标节点的 `authorized_keys` 里给这把 key 加限制，
      禁掉端口转发 / agent 转发 / pty：
      ```
      restrict ssh-ed25519 AAAA... gpumon@monitor-host
      ```
      采集只需要执行命令和读 stdin，`restrict` 不影响它。改完必须用第 2 节的验证命令
      回归一遍再上线。
- [ ] **真实基础设施信息不入库。** `config/settings.toml` 和 `config/inventory.yaml`
      已在 `.gitignore` 里，因为它们含真实主机 key、SSH 别名和拓扑。
      `.gitignore` 同样排除了 `*.env`、`deploy/DEPLOYMENT-local.md` 和各类私钥。
      提交前扫一眼：
      ```bash
      git status --short           # 不该出现 inventory.yaml / settings.toml / *.env
      ```
- [ ] **口令 hash、DNS token、私钥只留在部署机本地**，`chmod 600`，绝不进仓库。
- [ ] **想隐去使用人姓名**（对外展示、隐私合规）：`settings.toml` 里
      `[privacy] mask_users = true`，网页显示成 `a***e`。

> **关于登录**：当前版本没有内置登录或授权系统。访问控制必须由反向代理的 Basic Auth
> （路径 2 / 3）或网络隔离（路径 1）提供；公网入口必须使用 HTTPS。

---

## 10. 排障

| 症状 | 可能原因 | 怎么查 / 怎么修 |
| --- | --- | --- |
| 某机 `online: false` | SSH 不通、别名写错、密钥没分发 | 看 `last_error`；用服务账户手动跑 `sudo -u <USER> ssh -o BatchMode=yes <alias> nvidia-smi -L`。**要用服务账户跑**，你自己能连不代表它能连（密钥和 `~/.ssh/config` 不是同一份） |
| 某机 `online: false`，`last_error` 是超时 | 跳板慢、网络抖动、节点负载高 | 调大 `settings.toml` 的 `ssh_connect_timeout_s` / `ssh_total_timeout_s`；`ssh -v <alias>` 看卡在哪一步 |
| 全部机器都离线 | 采集器没跑，或 `GPUMON_ROOT` 不对 | `systemctl status gpumon-collector`；`journalctl -u gpumon-collector -n 50` |
| `gpus_seen` 比 `gpus_expected` 少 | 卡掉了 / 掉总线，或 `gpu_count` 写错了 | 上机跑 `nvidia-smi -L \| wc -l`。真少了是硬件问题（查 `dmesg \| grep -i xid`）；数字本来就填错了就改 inventory 的 `gpu_count` |
| `gpus_seen` 是 `0` 或 `null` | 该账户跑不了 `nvidia-smi`，或驱动没起 | `ssh <alias> 'nvidia-smi'` 看报错。AMD 机器确认 `rocm-smi`/`amd-smi` 可用，必要时在 inventory 显式写 `vendor: amd` |
| `gpus_seen` 是 `null` 且没有任何错误 | 这台机从没采成功过（inventory 里有、库里还没有记录） | 先 `gpumon collect --once --host <key>` 单机跑通再说 |
| 网页能开但没数据 / 全是 `--` | 采集器没在跑，或数据库路径不一致 | `curl 127.0.0.1:8848/api/health` 看 `last_sample_age_s`；确认两个服务的 `GPUMON_ROOT` 指同一个目录（不一致会各写各的库） |
| 网页有数据但长时间窗空白 | 聚合表还没攒够数据，或保留天数太短 | `uv run gpumon rollup-once`；检查 `[retention]`：`raw_days` 必须 ≥ 最长时间窗 + 余量，否则「使用人排行」会少算 |
| 排行里同一个人裂成两行 | 长用户名被 `ps` 截断（`somebody` → `somebo+`） | 已修：探测脚本用 `ps -o user:32=` 定宽。注意 `-w`/`-ww` 只放宽整行、对 `user` 列无效，不能替代。修复前的历史行需单独回填 |
| 浏览器提示证书不受信 | 用的是 `tls internal`（自签） | 预期行为，点「继续」即可，流量仍加密。想要绿锁就走路径 2/3 |
| 证书签不下来（HTTP-01） | 入站 80 不可达，或 DNS 没生效 | `journalctl -u caddy \| grep -i acme`；`dig +short <YOUR_DOMAIN>` 核对；入站被封就改用 DNS-01（路径 3） |
| 证书签不下来（DNS-01） | token 错、插件没编进去、DNS 缓存 | `caddy list-modules \| grep dns.providers`（没输出 = 插件没带进来）；`tls` 块里加 `resolvers 1.1.1.1 8.8.8.8` |
| `curl` 在 TLS 握手阶段被 RST | 域名按 SNI 被阻断 | 加 IP 直连入口 + `default_sni`，见 7.5 |
| 口令怎么输都不对 | hash 里的 `$` 被 shell 展开了 | `/etc/gpumon/caddy.env` 里用单引号：`GPUMON_BASIC_HASH='$2a$14$...'`；改完 `systemctl restart caddy`（不是 reload） |
| Caddy 起不来 | 指令名版本不符、环境文件未加载、端口被占 | 用 6.4 节“加载环境文件 + 显式 adapter”的 validate 命令；≥2.8 用 `basic_auth`，更早用 `basicauth`；`ss -tlnp \| grep -E ':(443\|8443)'` |
| 数据库 `database is locked` | 两个采集器同时在跑 | 用户级和系统级只能留一套：`systemctl --user disable --now gpumon-collector` |
| 改了 inventory 网页没反应 | 采集器只在启动时读配置 | `systemctl restart gpumon-collector`（退役机器还要一起重启 `gpumon-web`） |

采集不到时最快的定位手段 —— 直接看原始探测输出：

```bash
cd <ROOT> && ./scripts/probe_one.sh <ssh-alias>
```

它把远端脚本原样跑一遍并打印分段输出（`##META` / `##GPU` / `##APPS` ...）。
哪一段空、哪一段报错，一眼就能定位是 SSH 层、驱动层还是解析层的问题。

---

## 11. 卸载 / 回滚

```bash
sudo systemctl disable --now gpumon-collector gpumon-web caddy
sudo rm -f /etc/systemd/system/gpumon-*.service
sudo systemctl daemon-reload

# 彻底清理（按需）
sudo rm -rf /etc/gpumon /etc/caddy/Caddyfile
sudo userdel -r <USER>
# 从各目标节点的 ~/.ssh/authorized_keys 删掉部署公钥
# 关掉安全组 / 防火墙上放行的端口
```

数据库在 `<ROOT>/data/gpumon.db`，删目录前想留历史的话先备份走。
