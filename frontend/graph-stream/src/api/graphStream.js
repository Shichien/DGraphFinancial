export async function fetchGraphStream({ batchSize = 120, view = "window" } = {}) {
  const params = new URLSearchParams({ batch_size: String(batchSize), view });
  const response = await fetch(`/api/graph-stream?${params.toString()}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`图流接口请求失败：${response.status}`);
  }
  return response.json();
}

export async function resetGraphStream() {
  const response = await fetch("/api/graph-stream/reset", { method: "POST", cache: "no-store" });
  if (!response.ok) {
    throw new Error(`图流回放重置失败：${response.status}`);
  }
  return response.json();
}

export async function fetchDataSources() {
  const response = await fetch("/api/data-sources", { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`数据源列表请求失败：${response.status}`);
  }
  return response.json();
}

export async function switchDataSource(source) {
  const response = await fetch("/api/data-source", {
    method: "POST",
    cache: "no-store",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ source }),
  });
  if (!response.ok) {
    throw new Error(`数据源切换失败：${response.status}`);
  }
  return response.json();
}

export async function fetchNodeNeighborhood(nodeId, { scope = "full", limit = 120 } = {}) {
  const params = new URLSearchParams({
    node_id: String(nodeId),
    scope,
    limit: String(limit),
  });
  const response = await fetch(`/api/graph-node-neighborhood?${params.toString()}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`节点邻域接口请求失败：${response.status}`);
  }
  return response.json();
}

export async function fetchAuditLogs({ limit = 24 } = {}) {
  const params = new URLSearchParams({ limit: String(limit) });
  const response = await fetch(`/api/audit-logs?${params.toString()}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`审计日志接口请求失败：${response.status}`);
  }
  return response.json();
}

export async function fetchCaseActions({ limit = 24 } = {}) {
  const params = new URLSearchParams({ limit: String(limit) });
  const response = await fetch(`/api/case-actions?${params.toString()}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`案件处置接口请求失败：${response.status}`);
  }
  return response.json();
}

export async function recordCaseAction({ eventId, status, reviewer = "reviewer", note = "" }) {
  const response = await fetch("/api/case-actions", {
    method: "POST",
    cache: "no-store",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      event_id: eventId,
      status,
      reviewer,
      note,
    }),
  });
  if (!response.ok) {
    throw new Error(`案件处置写入失败：${response.status}`);
  }
  return response.json();
}

export async function fetchRiskConsoleSchema() {
  const response = await fetch("/api/risk-console/schema", { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`风险控制台元数据请求失败: ${response.status}`);
  }
  return response.json();
}

export async function runRiskConsole(payload) {
  const response = await fetch("/api/risk-console/run", {
    method: "POST",
    cache: "no-store",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error(detail.detail || `风险控制台执行失败: ${response.status}`);
  }
  return response.json();
}
