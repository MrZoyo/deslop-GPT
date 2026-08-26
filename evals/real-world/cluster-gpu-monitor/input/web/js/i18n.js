// 国际化管理器
window.I18n = {
  locale: 'zh',

  dict: {
    zh: {
      // 导航与面包屑
      'overview': '总览',
      'user_ranking': '用户排行',
      'back_to_overview': '‹ 返回总览',
      'back_to': '‹ 返回 {name}',

      // 顶栏控件
      'appearance': '外观：',
      'time_window': '时间窗：',
      'theme_dark': '夜间',
      'theme_light': '日间',
      'loading': '加载中…',
      'service_unreachable': '服务不可达',

      // 状态文字
      'online': '在线',
      'offline': '离线',
      'offline_n_times': '离线 {n} 次',
      'planned': '待接入',
      'idle': '空闲',
      'held': '空占',
      'active': '在用',
      'in_use': '在用',

      // KPI 指标
      'instant_util': '瞬时利用率',
      'instant_util_short': '瞬时',
      'window_avg': '{window} 平均',
      'window_avg_short': '窗口均值',
      'recent_util_10min': '近期利用率(10分钟)',
      'accumulating': '积累中',
      'data_accumulating': '积累中',
      'memory': '显存',
      'temperature': '温度',
      'power': '功耗',
      'coverage': '覆盖 {pct}%',
      'usage_idle': '空闲',
      'usage_held': '空占显存：{names}',
      'usage_active': '使用人：{names}',
      'unknown_user': '未知',
      'and_n_more': '等 {n} 人',
      'gpu_busy_discovered': 'GPU 在用 / 已发现',
      'coverage_hint': '接入覆盖 {discovered} / {expected}',
      'online_hosts': '在线主机',
      'planned_hosts': '待接入主机',
      'clusters': '集群',
      'hosts': '主机',
      'gpus': 'GPU',
      'current_avg': '当前均值',
      'avg': '均值',

      // 时间相关
      'updated_at': '更新于 {time}',
      'refresh_every': '每 {seconds} 秒刷新',
      'never': '从未',
      'ago_seconds': '{n} 秒前',
      'ago_minutes': '{n} 分钟前',
      'ago_hours': '{n} 小时前',
      'ago_days': '{n} 天前',
      'data_at': '数据 {time}',

      // 警报面板
      'offline_active_hosts': '离线已接入主机',
      'full_load_gpus': '满载 GPU',
      'planned_clusters': '待接入集群',
      'no_realtime_data': '暂无实时 GPU 数据',

      // 利用率图例
      'utilization_pct': '利用率 %',
      'expand_collapse': '展开 / 收起',

      // 主机行
      'host_system_info': 'CPU {cpu} · load {load} · 内存 {mem_used}/{mem_total}',
      'host_planned_info': '{gpu_model} · 规划 {count} GPU',
      'no_system_data': '无系统数据',
      'cards_seen': '{seen}/{expected} GPU',

      // 集群视图
      'cluster_index_machines': '{n} 集群 · {m} GPU',
      'view_cluster_detail': '查看 {name} 详情页（各主机卡阵 · 利用率时序 · 使用人 Top）',

      // 算力域
      'capacity_metrics_clusters': '集群',
      'capacity_metrics_hosts': '主机',
      'capacity_metrics_gpus': 'GPU',
      'capacity_metrics_avg': '当前均值',
      'no_devices': '暂无设备',
      'cluster_column': '集群',
      'status': '状态',

      // 多窗口对比表
      'compare_table_title': '各主机平均利用率 · 多时间窗对比',

      // 错误与空状态
      'load_failed': '加载失败',
      'empty_state': '暂无设备',

      // 健康状态
      'health_online': '在线 {online}/{total} · 数据 {time}',
      'health_host_online': '在线',
      'health_host_offline': '离线',
      'health_cards': '{seen}/{expected} GPU',

      // 集群视图
      'cluster_not_found': '未找到集群',
      'cluster_hosts_title': '各主机',
      'cluster_avg_util': '集群平均 GPU 利用率 · 近 {window}',
      'cluster_access_status': '接入状态',
      'cluster_planned_note': '该集群已预留容量，待 SSH/root 权限就绪后开始采集。',
      'cluster_top_users': '{name} · 使用人 Top · 近 {window}（按 GPU·小时）',
      'gpu_hours': 'GPU·小时',

      // 主机视图
      'host_not_found': '未找到主机',
      'host_cpu_util': 'CPU 利用率',
      'host_load_cores': 'load1 / 核数',
      'host_memory': '内存',
      'host_status': '状态',
      'host_offline_n': '离线（{n}次失败）',
      'host_last_error': '最近错误：',
      'host_gpu_title': 'GPU（点击看单卡趋势）',
      'host_planned_note': '该设备已预留，待 SSH/root 权限就绪后开始采集。',
      'host_gpu_util_chart': '各卡 GPU 利用率 · 近 {window}',
      'host_current_users_title': '当前使用人',
      'host_no_processes': '当前无 GPU 进程',
      'table_card': 'GPU',
      'table_user': '使用人',
      'table_process': '进程',
      'table_memory': '显存',

      // GPU 视图
      'gpu_not_found': '未找到该卡',
      'gpu_instant_util': '瞬时利用率',
      'gpu_memory': '显存',
      'gpu_temperature': '温度',
      'gpu_power': '功耗',
      'gpu_avg_util_windows': '平均利用率 · 各时间窗',
      'gpu_series_title': '时序 · 近 {window}',
      'gpu_metric_util': 'GPU 利用率',
      'gpu_metric_mem_util': '显存带宽利用率',
      'gpu_metric_mem_used': '显存占用',
      'gpu_metric_temp': '温度',
      'gpu_metric_power': '功耗',
      'gpu_current_users': '当前使用人',
      'gpu_idle': '当前空闲，无 GPU 进程',

      // 排行视图
      'ranking_title': '用户占用排行',
      'ranking_no_data': '近 {window} 暂无使用人数据（数据积累中）',
      'ranking_truncated': '用户较多，仅显示前 {shown}/{total} 名。',
      'ranking_chart_title': '用户占用排行 · 近 {window}（按 GPU·小时）',
      'ranking_note': '同一用户名跨机器累加；颜色按算力域分色系、同集群用相近色，可点图例隐藏某设备。切换顶部时间窗改统计区间。',
      'ranking_gpu_hours': 'GPU·小时',
      'ranking_no_usage': '无占用',
      'ranking_others_sum': '其余 {n} 台合计',
      'ranking_rank': '#',
      'ranking_user': '用户',
      'ranking_total': '合计 GPU·h',
      'ranking_collapse': '按集群合并（当前 {n} 列）',
      'ranking_expand': '展开到单机（{n} 台）',
      'ranking_detail_expanded': '明细 · 按算力域 / 集群分组（GPU·小时，跨设备）',
      'ranking_detail_collapsed': '明细 · 按算力域 / 集群汇总（GPU·小时）',
      'ranking_collapsed_note': '机器较多（{n} 台），已按集群合并列以免横向溢出；点右上角可展开到单机。',
      'ranking_other': '其他',

      // Demo Banner
      'demo_banner_title': '演示站点',
      'demo_banner_text': '数据为虚构示例（算力域 / 集群 / 用户名均为编造），时间冻结于导出时刻。',
      'demo_banner_link': '源码与部署说明 →',
    },

    en: {
      // Navigation & Breadcrumb
      'overview': 'Overview',
      'user_ranking': 'User Ranking',
      'back_to_overview': '‹ Back to Overview',
      'back_to': '‹ Back to {name}',

      // Topbar Controls
      'appearance': 'Theme:',
      'time_window': 'Window:',
      'theme_dark': 'Dark',
      'theme_light': 'Light',
      'loading': 'Loading…',
      'service_unreachable': 'Service Unreachable',

      // Status
      'online': 'Online',
      'offline': 'Offline',
      'offline_n_times': 'Offline ({n} fails)',
      'planned': 'Planned',
      'idle': 'Idle',
      'held': 'Held',
      'active': 'Active',
      'in_use': 'In Use',

      // KPI Metrics
      'instant_util': 'Instant Util',
      'instant_util_short': 'Instant',
      'window_avg': '{window} Avg',
      'window_avg_short': 'Window Avg',
      'recent_util_10min': 'Recent Util (10min)',
      'accumulating': 'Accumulating',
      'data_accumulating': 'Accumulating',
      'memory': 'Memory',
      'temperature': 'Temperature',
      'power': 'Power',
      'coverage': 'Coverage {pct}%',
      'usage_idle': 'Idle',
      'usage_held': 'Memory held: {names}',
      'usage_active': 'Users: {names}',
      'unknown_user': 'Unknown',
      'and_n_more': '+ {n} more',
      'gpu_busy_discovered': 'GPU Busy / Discovered',
      'coverage_hint': 'Coverage {discovered} / {expected}',
      'online_hosts': 'Online Hosts',
      'planned_hosts': 'Planned Hosts',
      'clusters': 'Clusters',
      'hosts': 'Hosts',
      'gpus': 'GPUs',
      'current_avg': 'Current Avg',
      'avg': 'Avg',

      // Time Related
      'updated_at': 'Updated {time}',
      'refresh_every': 'Refresh every {seconds}s',
      'never': 'Never',
      'ago_seconds': '{n}s ago',
      'ago_minutes': '{n}m ago',
      'ago_hours': '{n}h ago',
      'ago_days': '{n}d ago',
      'data_at': 'Data {time}',

      // Alert Panel
      'offline_active_hosts': 'Offline Active Hosts',
      'full_load_gpus': 'Full Load GPUs',
      'planned_clusters': 'Planned Clusters',
      'no_realtime_data': 'No Realtime GPU Data',

      // Utilization Legend
      'utilization_pct': 'Utilization %',
      'expand_collapse': 'Expand / Collapse',

      // Host Row
      'host_system_info': 'CPU {cpu} · load {load} · Memory {mem_used}/{mem_total}',
      'host_planned_info': '{gpu_model} · Planned {count} GPUs',
      'no_system_data': 'No System Data',
      'cards_seen': '{seen}/{expected} GPUs',

      // Cluster View
      'cluster_index_machines': '{n} clusters · {m} GPUs',
      'view_cluster_detail': 'View {name} details (host arrays · utilization trends · top users)',

      // Capacity Domain
      'capacity_metrics_clusters': 'Clusters',
      'capacity_metrics_hosts': 'Hosts',
      'capacity_metrics_gpus': 'GPUs',
      'capacity_metrics_avg': 'Current Avg',
      'no_devices': 'No Devices',
      'cluster_column': 'Cluster',
      'status': 'Status',

      // Compare Table
      'compare_table_title': 'Host Avg Util · Multi-Window Comparison',

      // Error & Empty State
      'load_failed': 'Load Failed',
      'empty_state': 'No Devices',

      // Health Status
      'health_online': 'Online {online}/{total} · Data {time}',
      'health_host_online': 'online',
      'health_host_offline': 'offline',
      'health_cards': '{seen}/{expected} GPUs',

      // Cluster View
      'cluster_not_found': 'Cluster Not Found',
      'cluster_hosts_title': 'Hosts',
      'cluster_avg_util': 'Cluster Avg GPU Util · Last {window}',
      'cluster_access_status': 'Access Status',
      'cluster_planned_note': 'This cluster is reserved. Data collection will start once SSH/root access is ready.',
      'cluster_top_users': '{name} · Top Users · Last {window} (by GPU·hours)',
      'gpu_hours': 'GPU·hours',

      // Host View
      'host_not_found': 'Host Not Found',
      'host_cpu_util': 'CPU Util',
      'host_load_cores': 'load1 / cores',
      'host_memory': 'Memory',
      'host_status': 'Status',
      'host_offline_n': 'Offline ({n} fails)',
      'host_last_error': 'Last error: ',
      'host_gpu_title': 'GPUs (click for per-GPU trends)',
      'host_planned_note': 'This device is reserved. Data collection will start once SSH/root access is ready.',
      'host_gpu_util_chart': 'Per-GPU GPU Util · Last {window}',
      'host_current_users_title': 'Current Users',
      'host_no_processes': 'No GPU processes currently',
      'table_card': 'GPU',
      'table_user': 'User',
      'table_process': 'Process',
      'table_memory': 'Memory',

      // GPU View
      'gpu_not_found': 'GPU Not Found',
      'gpu_instant_util': 'Instant Util',
      'gpu_memory': 'Memory',
      'gpu_temperature': 'Temperature',
      'gpu_power': 'Power',
      'gpu_avg_util_windows': 'Avg Util · Time Windows',
      'gpu_series_title': 'Series · Last {window}',
      'gpu_metric_util': 'GPU Util',
      'gpu_metric_mem_util': 'Memory Bandwidth Util',
      'gpu_metric_mem_used': 'Memory Used',
      'gpu_metric_temp': 'Temperature',
      'gpu_metric_power': 'Power',
      'gpu_current_users': 'Current Users',
      'gpu_idle': 'Currently idle, no GPU processes',

      // Ranking View
      'ranking_title': 'User Ranking',
      'ranking_no_data': 'No user data for last {window} (accumulating)',
      'ranking_truncated': 'Many users; showing the top {shown} of {total}.',
      'ranking_chart_title': 'User Ranking · Last {window} (by GPU·hours)',
      'ranking_note': 'Same username aggregated across machines. Colors by capacity group family, same cluster uses similar hues. Click legend to hide devices. Change time window in topbar to adjust range.',
      'ranking_gpu_hours': 'GPU·hours',
      'ranking_no_usage': 'No usage',
      'ranking_others_sum': '{n} others total',
      'ranking_rank': '#',
      'ranking_user': 'User',
      'ranking_total': 'Total GPU·h',
      'ranking_collapse': 'Collapse by cluster (currently {n} cols)',
      'ranking_expand': 'Expand to per-host ({n} hosts)',
      'ranking_detail_expanded': 'Detail · Grouped by Capacity / Cluster (GPU·hours, cross-device)',
      'ranking_detail_collapsed': 'Detail · Aggregated by Capacity / Cluster (GPU·hours)',
      'ranking_collapsed_note': 'Many machines ({n} hosts), collapsed by cluster to avoid overflow. Click button above to expand to per-host.',
      'ranking_other': 'Other',

      // Demo Banner
      'demo_banner_title': 'Demo Site',
      'demo_banner_text': 'Data is fictitious (capacity groups / clusters / usernames are made up), time frozen at export.',
      'demo_banner_link': 'Source & Deployment Guide →',
    }
  },

  t(key, params) {
    const text = this.dict[this.locale][key] || key;
    if (!params) return text;
    return text.replace(/\{(\w+)\}/g, (_, k) => params[k] ?? '');
  },

  // inventory 自定义文案支持旧字符串和 {locale: text} 两种形状。
  // 优先当前 locale，其次匹配同一基础语言，最后按配置顺序取第一条翻译。
  localize(value, locale) {
    if (typeof value === 'string') return value;
    if (!value || typeof value !== 'object' || Array.isArray(value)) return '';
    const entries = Object.entries(value).filter(([, text]) =>
      typeof text === 'string' && text.length > 0);
    if (!entries.length) return '';

    const wanted = String(locale || this.locale || '').toLowerCase();
    const exact = entries.find(([key]) => key.toLowerCase() === wanted);
    if (exact) return exact[1];

    const base = wanted.split('-')[0];
    const baseExact = entries.find(([key]) => key.toLowerCase() === base);
    if (baseExact) return baseExact[1];
    const sameLanguage = entries.find(([key]) => key.toLowerCase().split('-')[0] === base);
    return sameLanguage ? sameLanguage[1] : entries[0][1];
  },

  getLocale() {
    return this.locale;
  },

  setLocale(locale) {
    this.locale = locale;
    localStorage.setItem('gpumon.locale', locale);
    // 触发重新渲染
    if (window.GM) {
      if (GM.buildLangSwitch) GM.buildLangSwitch();
      if (GM.buildThemeSwitch) GM.buildThemeSwitch();
      if (GM.buildWinSwitch) GM.buildWinSwitch();
      if (GM.updateDemoBanner) GM.updateDemoBanner();
      // 更新 navRank 文字
      const navRankText = document.getElementById("navRankText");
      if (navRankText) navRankText.textContent = this.t('user_ranking');
      if (GM.render) GM.render();
    }
  },

  init() {
    const saved = localStorage.getItem('gpumon.locale');
    this.locale = (saved === 'en') ? 'en' : 'zh';
  }
};
