# Docker Compose 部署

简体中文 | [English](DOCKER.en.md) | [文档目录](README.md) | [项目首页](../README.md)

本项目支持两种常驻部署方式：

- [原生部署](DEPLOYMENT.md)：Python 虚拟环境、systemd、不可变 release 和 Caddy。
- Docker Compose：同一镜像分别运行 collector、Web 和一次性 backup 任务。

本文只讲 Docker Compose。两种方式使用相同的配置格式和 SQLite 数据库，但同一数据库同时
只能有一个 collector 写入。已经使用原生部署时，不要在它仍运行时启动容器 collector。

容器只在中心机上运行，通过 SSH 采集远端 GPU；不需要 NVIDIA Container Toolkit、
`--privileged` 或宿主 GPU 设备。

## 服务与权限边界

`compose.yaml` 从一个镜像启动三个不同职责：

| 服务 | SSH 目录 | 配置 | 数据目录 | 网络 |
| --- | --- | --- | --- | --- |
| `collector` | 只读 | 只读 | 读写 | 仅用于出站 SSH |
| `web` | 不挂载 | 只读 | 只读 | 隔离网络；端口只发布到宿主回环 |
| `backup` | 不挂载 | 只读 | 读写 | 完全禁用 |

三个服务都以非 root 用户运行，并启用只读根文件系统、全部 capability 删除、
`no-new-privileges`、PID 上限、内存上限和日志轮换。Web 仍然没有内置认证；团队访问必须经过
带认证的 HTTPS 反向代理。

## 前置条件

监控机需要：

- Linux 与 Docker Engine 24+。
- Docker Compose v2.24+，使用 `docker compose` 子命令。
- 到每台 GPU 节点的专用 SSH 配置、`known_hosts` 和密钥。
- 本机文件系统上的配置目录和数据目录；SQLite 数据不要放在 NFS 或对象存储挂载上。

目标 GPU 节点的要求与原生部署相同：普通账户能够运行厂商 SMI、`ps`、`bash` 和 coreutils。

## 1. 准备配置与数据目录

在仓库根目录执行：

```bash
cp config/inventory.example.yaml config/inventory.yaml
cp config/settings.example.toml config/settings.toml
cp deploy/docker/.env.example .env
```

编辑 `config/inventory.yaml` 和 `config/settings.toml`。容器会把整个 `config/` 只读挂载到
`/state/config`，把 `data/` 挂载到 `/state/data`。真实配置、数据库和 `.env` 已被 Git 忽略，
Docker 构建上下文也使用白名单，不会把它们送进镜像构建。

生产可以把状态移出 checkout，并在 `.env` 使用绝对路径：

```dotenv
GPUMON_CONFIG_DIR=/opt/gpu-monitor/config
GPUMON_DATA_DIR=/opt/gpu-monitor/data
```

数据目录必须由容器用户对应的 UID/GID 写入。

## 2. 准备专用 SSH 目录

不要把个人的整个 `~/.ssh` 挂进 collector。准备一个只服务 GPU Monitor 的目录，里面只放：

- `config`
- `known_hosts`
- 专用私钥及其公钥

容器内的 home 固定为 `/home/gpumon`，因此 SSH 配置可以继续使用相对 home 的密钥路径：

```sshconfig
Host gpu-node-1
    HostName <NODE_ADDRESS>
    User <REMOTE_USER>
    IdentityFile ~/.ssh/id_ed25519_gpumon
    StrictHostKeyChecking yes
```

ProxyJump、多级跳板和主机密钥策略与[原生部署的 SSH 配置](DEPLOYMENT.md#2-ssh-配置整套部署的地基)
相同。地址必须从容器网络可达；SSH 配置中的 `127.0.0.1` 指向容器自身，不是宿主。
SSH 目录在容器内只读，因此必须在启动 collector 前准备好 `known_hosts`；不要依赖容器首次
连接时用 `accept-new` 写入。

建议权限：SSH 目录 `0700`、私钥和 `config` 为 `0600`、`known_hosts` 为 `0644`。把目录的
绝对路径写进 `.env`：

```dotenv
GPUMON_SSH_DIR=/absolute/path/to/gpumon-ssh
```

## 3. 对齐容器 UID/GID

镜像默认创建 UID/GID 1000 的 `gpumon` 用户。把 `.env` 中的值改成拥有 SSH 目录和数据目录
的宿主用户 ID；分别运行 `id -u` 和 `id -g` 可以查看当前用户的值。

```dotenv
GPUMON_UID=1000
GPUMON_GID=1000
```

UID/GID 在镜像构建时生效。修改后必须重新运行 `docker compose build`。不要把 SSH 私钥改成
宽松权限来绕过 UID 不匹配。

## 4. 构建并试采

先渲染 Compose 配置，确认必填变量和语法：

```bash
docker compose config --quiet
docker compose build
```

容器内先做不会发起 SSH 的配置校验，再试采一轮：

```bash
docker compose run --rm --no-deps collector config-check
docker compose run --rm --no-deps collector collect --once
```

第二条命令会初始化 SQLite、写入一轮样本并执行聚合。若所有目标都失败，它会以非零状态退出；
先解决 SSH 或远端依赖问题，再启动常驻服务。

## 5. 启动与访问

```bash
docker compose up -d collector web
docker compose ps
curl --max-time 5 -fsS http://127.0.0.1:8848/api/live
curl --max-time 5 -fsS http://127.0.0.1:8848/api/health
```

默认只发布 `127.0.0.1:8848`。本机打开 `http://127.0.0.1:8848/`；从另一台电脑访问时，使用
SSH 隧道：

```bash
ssh -N -L 8848:127.0.0.1:8848 <monitor-host>
```

团队共享时，让宿主 Caddy、Nginx 或其它反向代理访问 `127.0.0.1:8848`，并在代理层配置 HTTPS
和认证。除非外层网络已经完成等价保护，否则不要把 `GPUMON_WEB_BIND` 改成 `0.0.0.0`。

## 6. 日常操作

查看有上限的近期日志：

```bash
docker compose logs --tail 100 collector
docker compose logs --tail 100 web
```

修改 inventory 或 settings 后重启两个常驻服务，让进程重新加载配置：

```bash
docker compose restart collector web
```

停止服务不会删除宿主配置和数据：

```bash
docker compose down
```

不要使用 `docker compose up --scale collector=2`。SQLite 架构要求 collector 始终只有一个实例。

## 7. 备份与定时调度

手工备份使用一次性、无网络的 backup 服务：

```bash
docker compose run --rm --no-deps backup
```

备份通过 SQLite backup API 写到宿主的 `data/backups/`，校验成功后才原子发布并按
`keep_count` 清理旧文件。不要直接复制正在写入的 `gpumon.db`、WAL 或 SHM 文件。

Compose 本身不提供定时器。生产请选择一个宿主调度器，每天只触发下面这一条命令：

```bash
cd /absolute/path/to/cluster-gpu-monitor && \
  /usr/bin/docker compose run --rm --no-deps backup backup --scheduled
```

`--scheduled` 会读取 `backup.enabled`；设为 `false` 时安全跳过。systemd timer、cron、NAS 任务
计划或平台调度器任选其一，禁止同时启用多个备份调度源。

## 8. 升级与回滚

升级前先备份数据库，并为当前镜像保留一个本地回滚标签：

```bash
docker compose run --rm --no-deps backup
docker image tag "$(docker compose images -q collector)" cluster-gpu-monitor:rollback
git pull --ff-only
docker compose build --pull
```

先更新 collector，确认新样本继续推进，再更新 Web：

```bash
docker compose up -d --no-deps collector
curl --max-time 5 -fsS http://127.0.0.1:8848/api/health
docker compose up -d --no-deps web
curl --max-time 5 -fsS http://127.0.0.1:8848/api/health
```

若新版本失败，使用保留的旧镜像恢复两个服务：

```bash
GPUMON_IMAGE=cluster-gpu-monitor:rollback \
  docker compose up -d --no-deps collector web
```

确认回滚稳定后再排查新镜像。不要在故障期间同时启动新旧 collector。

## 9. 排障

### SSH 权限错误

确认 `.env` 的 UID/GID 与 SSH 目录所有者一致，私钥仍为 `0600`。只检查文件属性，不要把私钥
内容贴到日志、issue 或聊天中。可以在 collector 容器内验证某个 alias 是否能解析并登录：

```bash
docker compose run --rm --no-deps --entrypoint ssh collector \
  -o BatchMode=yes -o ConnectTimeout=10 <ssh-alias> true
```

### Web 无法打开

依次检查进程、健康端点和最近日志：

```bash
docker compose ps web
curl --max-time 5 -fsS http://127.0.0.1:8848/api/live
docker compose logs --tail 100 web
```

`/api/live` 只确认进程响应；`/api/health` 还检查配置、数据库和样本新鲜度。

### 数据目录不可写

确认 `GPUMON_DATA_DIR` 指向本机目录，目录所有者与 `.env` 中的 UID/GID 一致，而且没有把
collector 的数据挂载改成只读。不要通过以 root 运行容器来掩盖权限问题。

## 安全清单

- [ ] 构建上下文来自干净的公开仓库，不包含私有 overlay。
- [ ] collector 只挂载专用 SSH 目录，Web 和 backup 看不到任何 SSH 文件。
- [ ] Web 只发布到宿主回环，外部访问经过 HTTPS 和认证。
- [ ] 配置只读挂载，Web 数据只读挂载。
- [ ] SQLite 位于本机文件系统，而且只有一个 collector。
- [ ] 自动备份只有一个调度源，并已验证 `data/backups/` 出现可用备份。
- [ ] 没有挂载 Docker socket，也没有启用 privileged 或额外 capability。
