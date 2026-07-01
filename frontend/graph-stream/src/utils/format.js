export const levelColor = {
  critical: "#c43b32",
  high: "#bc7a1b",
  medium: "#2e6d8f",
  low: "#1f7a62",
};

export const levelText = {
  critical: "严重",
  high: "高危",
  medium: "中危",
  low: "低危",
};

export const truthText = {
  fraud: "欺诈样本",
  normal: "正常样本",
  background: "背景节点",
};

export const channelText = {
  bank_transfer: "银行转账",
  wallet_pay: "钱包支付",
  merchant_acquire: "商户收单",
  mobile_banking: "手机银行",
  wallet: "钱包",
  bank_app: "银行应用",
  qr_pay: "扫码支付",
  web: "网页",
  merchant_api: "商户接口",
  node_probe: "节点探测",
  related_node: "关联节点",
  related: "关联关系",
  device_shared: "共同设备",
  ip_shared: "共同 IP",
  merchant_shared: "共同商户",
  account_transfer: "账户转账",
  runtime: "实时关系",
  unknown: "未知渠道",
};

export const actionText = {
  block: "自动拦截",
  review: "转入复核",
  step_up: "加强验证",
  step_up_verification: "加强验证",
  pass: "放行",
  manual_review: "人工复核",
  freeze_and_manual_review: "冻结并人工复核",
  pending_review: "待复核",
  confirmed_fraud: "确认欺诈",
  false_positive: "误报放行",
  manual_block: "人工冻结",
  released: "解除限制",
  auto_pass: "自动放行",
};

export const reasonText = {
  "account historical risk": "账户历史风险偏高",
  "behavior burst": "短时间交易突增",
  "amount large": "单笔金额偏大",
  "blacklist hit": "命中风险名单",
  "device reuse": "同一设备被多个账户复用",
  "device shared": "同一设备被多个账户复用",
  "ip cluster": "同一 IP 聚集多个账户",
  "merchant laundering": "疑似商户洗钱",
  "graph community": "团伙邻域风险",
  "rule multi hit": "多条规则同时命中",
  "cross channel": "跨渠道规避",
  "probe then drain": "小额试探后大额转移",
  "fan in cashout": "分散汇入后集中转出",
  "cycle transfer": "团伙循环转账",
  "offline model": "离线模型风险较高",
  "realtime behavior": "实时行为异常",
  "rule score": "规则分偏高",
  "script pattern matched": "命中欺诈剧本",
  "script pattern": "命中欺诈剧本",
  "device shared": "同一设备被多个账户复用",
  "ip shared": "同一 IP 聚集多个账户",
  "merchant shared": "商户关系异常",
  "community risk": "团伙邻域风险",
};

export const evidenceText = {
  fraud_script_type: "命中剧本",
  graph_community_id: "团伙编号",
  device_account_count: "共用设备账户数",
  ip_account_count: "同 IP 账户数",
  burst_score: "突发交易强度",
  amount: "交易金额",
  source_channel: "交易渠道",
  graph_neighbor_count: "相关邻居数",
  offline_model_score: "离线模型分",
  realtime_behavior_score: "实时行为分",
  graph_community_score: "团伙关系分",
  rule_score: "规则分",
  src_account: "源账户",
  dst_account: "目标账户",
  device_id: "设备编号",
  ip: "IP 地址",
  merchant_id: "商户编号",
  scenario_id: "场景编号",
  is_scripted_fraud: "剧本注入",
  risk_level: "风险等级",
  decision: "处置建议",
};

export const fraudScriptText = {
  fan_in_cashout: "分散汇入后集中转出",
  probe_then_drain: "小额试探后大额转移",
  cycle_transfer: "团伙循环转账",
  device_reuse: "设备复用",
  ip_cluster: "IP 聚集",
  merchant_laundering: "商户洗钱",
  cross_channel_evasion: "跨渠道规避",
  burst_window: "窗口内突发交易",
  burst_transfer: "突发转账",
  none: "未标注剧本",
  unknown: "未标注剧本",
};

export const graphFilterText = {
  all: "全部",
  high: "只看高危",
  community: "只看团伙",
  device_reuse: "设备复用",
  ip_cluster: "IP 聚集",
  merchant_laundering: "商户洗钱",
};

export function formatNumber(value) {
  return new Intl.NumberFormat("zh-CN").format(Number(value || 0));
}

export function formatScore(value) {
  return Number.isFinite(Number(value)) ? Number(value).toFixed(4) : "--";
}

export function formatReadableTime(value) {
  if (value === undefined || value === null || value === "") return "--";
  const date = parseTimeValue(value);
  if (!date) return String(value);
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(date);
}

export function formatReadableDateTime(value) {
  if (value === undefined || value === null || value === "") return "--";
  const date = parseTimeValue(value);
  if (!date) return String(value);
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(date);
}

export function riskLabel(level) {
  return levelText[level] || "未知";
}

export function truthLabel(label) {
  return truthText[label] || "未知样本";
}

export function channelLabel(channel) {
  const key = normalizeKey(channel);
  return channelText[key] || "未知渠道";
}

export function fraudScriptLabel(script) {
  const key = normalizeKey(script);
  if (!key) return "未标注剧本";
  return fraudScriptText[key] || "未识别剧本";
}

export function graphFilterLabel(mode) {
  return graphFilterText[mode] || "全部";
}

export function actionLabel(action) {
  const key = normalizeKey(action);
  return actionText[key] || "待处置";
}

export function communityLabel(communityId) {
  const value = String(communityId || "");
  if (!value) return "暂无团伙编号";
  const match = value.match(/comm[-_](.+)$/);
  if (match) return `团伙 ${match[1]}`;
  if (/^\d+$/.test(value)) return `团伙 ${value}`;
  return `团伙 ${value.replace(/^comm[-_]/, "").replace(/[_-]+/g, " ")}`;
}

export function reasonLabel(code) {
  const normalized = String(code || "")
    .replace(/[:_-]/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .toLowerCase();
  if (!normalized) return "模型评分命中";
  return reasonText[normalized] || "模型规则命中";
}

export function reasonSummary(codes, limit = 2) {
  const items = Array.isArray(codes) ? codes : [];
  if (items.length === 0) return "模型评分命中";
  return items.slice(0, limit).map(reasonLabel).join("；");
}

export function evidenceLabel(key) {
  return evidenceText[normalizeKey(key)] || "其他证据";
}

export function evidenceValueLabel(key, value) {
  if (value === undefined || value === null || value === "") return "暂无";
  const normalizedKey = normalizeKey(key);
  if (normalizedKey.includes("timestamp") || normalizedKey.includes("event_time") || normalizedKey.endsWith("_time") || normalizedKey.includes("created_at") || normalizedKey.includes("updated_at")) {
    return formatReadableDateTime(value);
  }
  if (normalizedKey === "source_channel" || normalizedKey.includes("channel")) return channelLabel(value);
  if (normalizedKey === "graph_community_id" || normalizedKey.includes("community")) return communityLabel(value);
  if (normalizedKey === "fraud_script_type" || normalizedKey.includes("script")) return fraudScriptLabel(value);
  if (normalizedKey === "decision" || normalizedKey.includes("action") || normalizedKey.includes("status")) return actionLabel(value);
  if (normalizedKey === "risk_level") return riskLabel(value);
  if (typeof value === "boolean") return value ? "是" : "否";
  if (typeof value === "number") return Number.isInteger(value) ? formatNumber(value) : formatScore(value);
  const normalizedValue = normalizeKey(value);
  if (channelText[normalizedValue]) return channelLabel(value);
  if (fraudScriptText[normalizedValue]) return fraudScriptLabel(value);
  if (actionText[normalizedValue]) return actionLabel(value);
  if (/^comm[-_]/i.test(String(value))) return communityLabel(value);
  return String(value);
}

export function normalizeKey(value) {
  return String(value || "")
    .trim()
    .replace(/-/g, "_")
    .toLowerCase();
}

function parseTimeValue(value) {
  if (value instanceof Date) {
    return Number.isNaN(value.getTime()) ? null : value;
  }
  if (typeof value === "number" || /^-?\d+(\.\d+)?$/.test(String(value).trim())) {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) return null;
    if (numeric >= 1_000_000_000_000) return new Date(numeric);
    if (numeric >= 1_000_000_000) return new Date(numeric * 1000);
    const demoStart = Date.UTC(2026, 0, 1, 9, 0, 0);
    return new Date(demoStart + Math.max(0, numeric) * 1000);
  }
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}
