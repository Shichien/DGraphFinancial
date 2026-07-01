import { onBeforeUnmount, onMounted, reactive, unref, watch } from "vue";
import { fetchNodeNeighborhood } from "../api/graphStream";
import { formatScore } from "../utils/format";

const levelColor = { critical: "#c43b32", high: "#bc7a1b", medium: "#2e6d8f", low: "#1f7a62" };

function nodeColor(node) {
  if (node.riskLevel === "critical" || node.riskLevel === "high") return "#d94b42";
  if (node.riskLevel === "medium") return "#d18b24";
  if (node.groundTruth === "background") return "#8fa0a0";
  return "#45b591";
}

function roundedRect(ctx, x, y, width, height, radius) {
  const r = Math.min(radius, width / 2, height / 2);
  ctx.moveTo(x + r, y);
  ctx.lineTo(x + width - r, y);
  ctx.quadraticCurveTo(x + width, y, x + width, y + r);
  ctx.lineTo(x + width, y + height - r);
  ctx.quadraticCurveTo(x + width, y + height, x + width - r, y + height);
  ctx.lineTo(x + r, y + height);
  ctx.quadraticCurveTo(x, y + height, x, y + height - r);
  ctx.lineTo(x, y + r);
  ctx.quadraticCurveTo(x, y, x + r, y);
}

function stableUnit(nodeId, salt) {
  const value = Math.sin((Number(nodeId) + salt) * 12.9898) * 43758.5453;
  return value - Math.floor(value);
}

function edgePathKind(edge, event = null) {
  const channel = String(edge.channel || edge.relation_type || edge.sourceScope || "").toLowerCase();
  const scriptType = String(event?.evidence?.fraud_script_type || "").toLowerCase();
  const reasons = Array.isArray(event?.reasonCodes) ? event.reasonCodes.join(" ").toLowerCase() : "";
  if (channel.includes("device") || scriptType.includes("device") || reasons.includes("device")) return "device";
  if (channel.includes("ip") || scriptType.includes("ip") || reasons.includes("ip")) return "ip";
  if (channel.includes("merchant") || scriptType.includes("merchant") || reasons.includes("merchant")) return "merchant";
  if (channel.includes("related")) return "community";
  return "fund";
}

function pathStrokeStyle(kind, selectedPath, focusPath, risky, medium, depthAlpha) {
  if (selectedPath || focusPath) {
    if (kind === "device") return ["rgba(88,166,255,0.92)", "rgba(88,166,255,0.62)"];
    if (kind === "ip") return ["rgba(183,132,255,0.92)", "rgba(183,132,255,0.62)"];
    if (kind === "merchant") return ["rgba(255,175,82,0.92)", "rgba(255,175,82,0.62)"];
    if (kind === "community") return ["rgba(255,213,112,0.88)", "rgba(217,75,66,0.68)"];
    return ["rgba(255,253,246,0.88)", "rgba(72,165,141,0.68)"];
  }
  const lowAlpha = 0.12 * depthAlpha;
  const mediumAlpha = 0.34 * depthAlpha;
  const riskAlpha = 0.58 * depthAlpha;
  if (risky) return [`rgba(217,75,66,${riskAlpha})`, `rgba(188,122,27,${riskAlpha * 0.9})`];
  if (medium) return [`rgba(209,139,36,${mediumAlpha})`, `rgba(72,165,141,${mediumAlpha * 0.86})`];
  return [`rgba(220,232,226,${lowAlpha})`, `rgba(72,165,141,${lowAlpha * 0.82})`];
}

export function useGraphCanvas(canvasRef, snapshotRef, replayTokenRef = null, options = {}) {
  return useGraphCanvasWithOptions(canvasRef, snapshotRef, replayTokenRef, options);
}

export function useGraphCanvasWithOptions(canvasRef, snapshotRef, replayTokenRef = null, options = {}) {
  const graphState = reactive({
    nodes: new Map(),
    snapshot: null,
    visibleNodes: [],
    visibleEdges: [],
    view: { rotX: -0.24, rotY: 0.58, zoom: 1.16 },
    drag: { active: false, pointerId: null, startX: 0, startY: 0, originRotX: 0, originRotY: 0, moved: false },
    focusNodeId: null,
    focusMode: "screen",
    focusLoading: false,
    focusError: "",
    neighborhood: null,
    focusNeighborCount: 0,
    focusEdgeCount: 0,
    recentNewNodeCount: 0,
    frameId: null,
    replayStartedAt: 0,
    replayDurationMs: 2600,
    lastSnapshotPosition: null,
  });

  const selectedEventRef = options.selectedEventRef || null;
  const focusNodeIdRef = options.focusNodeIdRef || null;
  const filterModeRef = options.filterModeRef || null;
  const legendStateRef = options.legendStateRef || null;
  const timelineProgressRef = options.timelineProgressRef || null;
  const graphModeRef = options.graphModeRef || null;
  const emitFocusChange = typeof options.onFocusChange === "function" ? options.onFocusChange : null;
  let lastVisibleIds = new Set();

  watch(snapshotRef, (snapshot) => {
    graphState.snapshot = snapshot;
  });

  if (replayTokenRef) {
    watch(replayTokenRef, () => {
      graphState.nodes.clear();
      clearFocus();
      graphState.replayStartedAt = performance.now();
    });
  }

  if (focusNodeIdRef) {
    watch(
      focusNodeIdRef,
      (nodeId) => {
        const normalized = nodeId === null || nodeId === undefined || nodeId === "" ? null : Number(nodeId);
        if (normalized === null) {
          if (graphState.focusNodeId !== null) clearFocus(false);
          return;
        }
        if (graphState.focusNodeId === normalized) return;
        focusNodeById(normalized, false);
      },
      { immediate: true },
    );
  }

  function optionValue(optionRef, fallback) {
    const value = unref(optionRef);
    return value === undefined || value === null ? fallback : value;
  }

  function selectedEvent() {
    return optionValue(selectedEventRef, null);
  }

  function currentFilterMode() {
    return optionValue(filterModeRef, "all");
  }

  function currentLegendState() {
    return optionValue(legendStateRef, { normal: true, review: true, fraud: true, related: true });
  }

  function currentTimelineProgress() {
    const value = Number(optionValue(timelineProgressRef, 1));
    if (!Number.isFinite(value)) return 1;
    return Math.max(0, Math.min(1, value));
  }

  function shouldRetainInactiveNodes() {
    return optionValue(graphModeRef, "window") === "cumulative";
  }

  function ensureCloudPoint(node) {
    const nodeId = Number(node.id);
    const existing = graphState.nodes.get(nodeId) || {};
    if (existing.cloud) return existing.cloud;
    const theta = stableUnit(nodeId, 1.7) * Math.PI * 2;
    const phi = Math.acos(2 * stableUnit(nodeId, 9.3) - 1);
    const radius = 0.82 + stableUnit(nodeId, 4.1) * 1.06;
    const clusterBias = (node.riskScore - 0.36) * 0.18;
    const band = Math.floor(stableUnit(nodeId, 12.8) * 5) - 2;
    const lateralSpread = (stableUnit(nodeId, 21.6) - 0.5) * 0.72;
    const verticalSpread = band * 0.18 + (stableUnit(nodeId, 6.4) - 0.5) * 0.22;
    return {
      x: Math.sin(phi) * Math.cos(theta) * radius + clusterBias + lateralSpread,
      y: Math.cos(phi) * radius * 0.78 + verticalSpread,
      z: Math.sin(phi) * Math.sin(theta) * radius - clusterBias * 0.3 + (stableUnit(nodeId, 31.3) - 0.5) * 0.64,
    };
  }

  function projectPoint(point, width, height) {
    const cosY = Math.cos(graphState.view.rotY);
    const sinY = Math.sin(graphState.view.rotY);
    const cosX = Math.cos(graphState.view.rotX);
    const sinX = Math.sin(graphState.view.rotX);
    const x1 = point.x * cosY - point.z * sinY;
    const z1 = point.x * sinY + point.z * cosY;
    const y1 = point.y * cosX - z1 * sinX;
    const z2 = point.y * sinX + z1 * cosX;
    const depth = z2 + 3.15;
    const perspective = (0.92 / depth) * graphState.view.zoom;
    const scale = Math.min(width, height) * 1.08;
    return {
      x: width * 0.54 + x1 * scale * perspective,
      y: height * 0.5 + y1 * scale * perspective,
      z: z2,
      depth,
      perspective,
      alpha: Math.max(0.2, Math.min(1, 1.1 - depth * 0.18)),
    };
  }

  function updateNodeLayout(nodes, width, height) {
    const now = performance.now();
    const visibleIds = new Set(nodes.map((node) => Number(node.id)));
    if (!shouldRetainInactiveNodes()) {
      graphState.nodes.forEach((_, nodeId) => {
        if (!visibleIds.has(Number(nodeId))) graphState.nodes.delete(nodeId);
      });
    }
    nodes.forEach((node, index) => {
      const nodeId = Number(node.id);
      const existing = graphState.nodes.get(nodeId) || {};
      const cloud = ensureCloudPoint(node);
      const bornAt = existing.bornAt || now;
      const drift = now * 0.00022 + index * 0.11;
      const eventPulse = 1 + Math.sin(now * 0.0024 + nodeId * 0.17) * 0.006;
      const animatedCloud = {
        x: cloud.x * eventPulse + Math.sin(drift + node.riskScore * 2) * 0.036,
        y: cloud.y + Math.cos(drift * 1.2) * 0.026,
        z: cloud.z * eventPulse + Math.sin(drift * 0.8) * 0.034,
      };
      const projected = projectPoint(animatedCloud, width, height);
      graphState.nodes.set(nodeId, { ...node, id: nodeId, ...projected, cloud, bornAt });
    });
  }

  function focusedGraph(nodes, edges) {
    if (graphState.focusNodeId === null) {
      graphState.focusNeighborCount = 0;
      graphState.focusEdgeCount = 0;
      return { nodes, edges };
    }
    if (Number(graphState.neighborhood?.focusNode) === Number(graphState.focusNodeId)) {
      const neighborhoodNodes = graphState.neighborhood.nodes || [];
      const neighborhoodEdges = graphState.neighborhood.edges || [];
      graphState.focusNeighborCount = Math.max(neighborhoodNodes.length - 1, 0);
      graphState.focusEdgeCount = neighborhoodEdges.length;
      return { nodes: neighborhoodNodes, edges: neighborhoodEdges };
    }
    const nodeIds = new Set(nodes.map((node) => Number(node.id)));
    if (!nodeIds.has(Number(graphState.focusNodeId))) {
      graphState.focusNodeId = null;
      graphState.focusNeighborCount = 0;
      graphState.focusEdgeCount = 0;
      return { nodes, edges };
    }
    const relatedIds = new Set([Number(graphState.focusNodeId)]);
    const relatedEdges = edges.filter((edge) => {
      const source = Number(edge.source);
      const target = Number(edge.target);
      if (source !== Number(graphState.focusNodeId) && target !== Number(graphState.focusNodeId)) return false;
      relatedIds.add(source);
      relatedIds.add(target);
      return true;
    });
    graphState.focusNeighborCount = Math.max(relatedIds.size - 1, 0);
    graphState.focusEdgeCount = relatedEdges.length;
    return {
      nodes: nodes.filter((node) => relatedIds.has(Number(node.id))),
      edges: relatedEdges,
    };
  }

  function eventMatchesMode(event, mode) {
    if (!event || mode === "all") return false;
    if (mode === "high") return event.riskLevel === "critical" || event.riskLevel === "high";
    if (mode === "community") return Boolean(event.communityId || event.evidence?.graph_community_id || event.relatedNodes?.length);
    const scriptType = event.evidence?.fraud_script_type;
    const reasons = Array.isArray(event.reasonCodes) ? event.reasonCodes.join(" ") : "";
    if (mode === "device_reuse") return scriptType === "device_reuse" || reasons.includes("device:shared");
    if (mode === "ip_cluster") return scriptType === "ip_cluster" || reasons.includes("ip:cluster");
    if (mode === "merchant_laundering") return scriptType === "merchant_laundering" || reasons.includes("merchant:laundering");
    return false;
  }

  function nodeLegendKey(node) {
    if (node.detectedFraud || node.riskLevel === "critical" || node.riskLevel === "high") return "fraud";
    if (node.riskLevel === "medium" || node.action === "manual_review" || node.action === "review") return "review";
    return "normal";
  }

  function filteredGraph(nodes, edges) {
    const mode = currentFilterMode();
    const legend = currentLegendState();
    const currentEvent = selectedEvent();
    let allowedIds = null;
    if (mode === "high") {
      allowedIds = new Set(
        nodes
          .filter((node) => node.riskLevel === "critical" || node.riskLevel === "high" || node.detectedFraud)
          .map((node) => Number(node.id)),
      );
    } else if (mode !== "all") {
      allowedIds = new Set();
      const events = graphState.snapshot?.recentEvents || [];
      events.filter((event) => eventMatchesMode(event, mode)).forEach((event) => {
        [event.focusNode, event.srcNode, event.dstNode].forEach((id) => {
          if (id !== undefined && id !== null) allowedIds.add(Number(id));
        });
        (event.relatedNodes || []).forEach((id) => allowedIds.add(Number(id)));
      });
      if (currentEvent && eventMatchesMode(currentEvent, mode)) {
        [currentEvent.focusNode, currentEvent.srcNode, currentEvent.dstNode].forEach((id) => {
          if (id !== undefined && id !== null) allowedIds.add(Number(id));
        });
        (currentEvent.relatedNodes || []).forEach((id) => allowedIds.add(Number(id)));
      }
    }

    const selectedIds = new Set((currentEvent?.relatedNodes || []).map((id) => Number(id)));
    [currentEvent?.focusNode, currentEvent?.srcNode, currentEvent?.dstNode, graphState.focusNodeId].forEach((id) => {
      if (id !== undefined && id !== null) selectedIds.add(Number(id));
    });

    const visibleNodes = nodes.filter((node) => {
      const nodeId = Number(node.id);
      if (allowedIds && allowedIds.size > 0 && !allowedIds.has(nodeId) && !selectedIds.has(nodeId)) return false;
      if (allowedIds && allowedIds.size === 0 && !selectedIds.has(nodeId)) return false;
      const key = nodeLegendKey(node);
      return legend[key] !== false || selectedIds.has(nodeId);
    });
    const visibleIds = new Set(visibleNodes.map((node) => Number(node.id)));
    const visibleEdges = edges.filter((edge) => {
      const source = Number(edge.source);
      const target = Number(edge.target);
      if (!visibleIds.has(source) || !visibleIds.has(target)) return false;
      if (legend.related === false && !selectedIds.has(source) && !selectedIds.has(target)) return false;
      return true;
    });
    return { nodes: visibleNodes, edges: visibleEdges };
  }

  function replaySlice(nodes, edges) {
    const timelineProgress = currentTimelineProgress();
    if (timelineProgress < 0.995) {
      const eventLimit = Math.max(1, Math.ceil((graphState.snapshot?.recentEvents?.length || nodes.length || 1) * timelineProgress));
      const visibleEvents = (graphState.snapshot?.recentEvents || []).slice(-eventLimit);
      if (visibleEvents.length) {
        const allowedIds = new Set();
        const allowedEdgeIds = new Set();
        visibleEvents.forEach((event) => {
          [event.srcNode, event.dstNode, event.focusNode].forEach((id) => {
            if (id !== undefined && id !== null) allowedIds.add(Number(id));
          });
          (event.relatedNodes || []).forEach((id) => allowedIds.add(Number(id)));
          allowedEdgeIds.add(`rt-${event.eventId}`);
        });
        return {
          nodes: nodes.filter((node) => allowedIds.has(Number(node.id))),
          edges: edges.filter((edge) => {
            const source = Number(edge.source);
            const target = Number(edge.target);
            return allowedIds.has(source) && allowedIds.has(target) && (allowedEdgeIds.has(String(edge.id)) || String(edge.id).startsWith("rel-"));
          }),
        };
      }
    }
    if (!graphState.replayStartedAt) {
      return { nodes, edges };
    }
    const elapsed = performance.now() - graphState.replayStartedAt;
    const progress = Math.min(1, elapsed / graphState.replayDurationMs);
    if (progress >= 1) {
      graphState.replayStartedAt = 0;
      return { nodes, edges };
    }
    const minimumNodes = Math.min(nodes.length, 8);
    const visibleNodeCount = Math.min(nodes.length, Math.max(minimumNodes, Math.ceil(nodes.length * progress)));
    const visibleNodes = nodes.slice(0, visibleNodeCount);
    const visibleIds = new Set(visibleNodes.map((node) => Number(node.id)));
    const visibleEdgeCount = Math.min(edges.length, Math.ceil(edges.length * Math.max(0, progress - 0.08) / 0.92));
    const visibleEdges = edges
      .slice(0, visibleEdgeCount)
      .filter((edge) => visibleIds.has(Number(edge.source)) && visibleIds.has(Number(edge.target)));
    return { nodes: visibleNodes, edges: visibleEdges };
  }

  function pickNode(clientX, clientY) {
    const canvas = canvasRef.value;
    if (!canvas || !graphState.snapshot) return null;
    const rect = canvas.getBoundingClientRect();
    const x = clientX - rect.left;
    const y = clientY - rect.top;
    const rawNodes = graphState.snapshot.nodes || [];
    const rawEdges = graphState.snapshot.edges || [];
    const filtered = filteredGraph(rawNodes, rawEdges);
    const { nodes } = focusedGraph(filtered.nodes, filtered.edges);
    let best = null;
    for (const node of nodes) {
      const point = graphState.nodes.get(Number(node.id));
      if (!point) continue;
      const radius = Math.max(8, (point.drawRadius || 3) + 6);
      const distance = Math.hypot(point.x - x, point.y - y);
      if (distance <= radius && (!best || distance < best.distance || point.depth < best.depth)) {
        best = { node, distance, depth: point.depth };
      }
    }
    return best?.node || null;
  }

  async function focusNode(node) {
    await setFocusNode(node, true);
  }

  async function setFocusNode(node, shouldEmit) {
    graphState.focusNodeId = Number(node.id);
    graphState.focusMode = "full";
    graphState.focusLoading = true;
    graphState.focusError = "";
    graphState.neighborhood = null;
    if (shouldEmit && emitFocusChange) emitFocusChange(Number(node.id));
    try {
      const neighborhood = await fetchNodeNeighborhood(node.id, { scope: "full", limit: 140 });
      if (graphState.focusNodeId !== Number(node.id)) return;
      if (neighborhood.available) {
        graphState.neighborhood = neighborhood;
        graphState.focusNeighborCount = Math.max((neighborhood.nodes || []).length - 1, 0);
        graphState.focusEdgeCount = (neighborhood.edges || []).length;
      } else {
        graphState.focusMode = "screen";
        graphState.focusError = "未找到完整邻域";
      }
    } catch {
      graphState.focusMode = "screen";
      graphState.focusError = "完整邻域加载失败，已使用当前窗口";
    } finally {
      if (graphState.focusNodeId === Number(node.id)) {
        graphState.focusLoading = false;
      }
    }
  }

  function focusNodeById(nodeId, shouldEmit = true) {
    const snapshot = graphState.snapshot || {};
    const node =
      (snapshot.nodes || []).find((item) => Number(item.id) === Number(nodeId)) ||
      (graphState.visibleNodes || []).find((item) => Number(item.id) === Number(nodeId)) ||
      { id: nodeId };
    return setFocusNode(node, shouldEmit);
  }

  function edgeInSelectedPath(edge) {
    const event = selectedEvent();
    if (!event) return false;
    const source = Number(edge.source);
    const target = Number(edge.target);
    const relatedIds = new Set((event.relatedNodes || []).map((id) => Number(id)));
    const hasRelatedNodes = relatedIds.has(source) && relatedIds.has(target);
    const hasRelatedEdges = (event.relatedEdges || []).some((item) => {
      const itemSource = Number(item.src_account ?? item.source);
      const itemTarget = Number(item.dst_account ?? item.target);
      return (itemSource === source && itemTarget === target) || (itemSource === target && itemTarget === source);
    });
    return hasRelatedNodes || hasRelatedEdges;
  }

  function edgeTouchesFocus(edge) {
    if (graphState.focusNodeId === null) return false;
    const source = Number(edge.source);
    const target = Number(edge.target);
    return source === Number(graphState.focusNodeId) || target === Number(graphState.focusNodeId);
  }

  function drawGraph() {
    const canvas = canvasRef.value;
    if (!canvas) {
      graphState.frameId = requestAnimationFrame(drawGraph);
      return;
    }
    const ctx = canvas.getContext("2d");
    const rect = canvas.getBoundingClientRect();
    const ratio = window.devicePixelRatio || 1;
    const width = Math.max(1, Math.floor(rect.width * ratio));
    const height = Math.max(1, Math.floor(rect.height * ratio));
    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width;
      canvas.height = height;
    }
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    ctx.clearRect(0, 0, rect.width, rect.height);
    if (!graphState.snapshot) {
      graphState.frameId = requestAnimationFrame(drawGraph);
      return;
    }

    const rawNodes = graphState.snapshot.nodes || [];
    const rawEdges = graphState.snapshot.edges || [];
    const replayed = replaySlice(rawNodes, rawEdges);
    const filtered = filteredGraph(replayed.nodes, replayed.edges);
    const { nodes, edges } = focusedGraph(filtered.nodes, filtered.edges);
    const latestEvent = graphState.snapshot.lastEvent || {};
    const animationClock = performance.now();
    const snapshotPosition = graphState.snapshot?.meta?.position ?? latestEvent.eventId ?? graphState.snapshot?.meta?.currentTimestamp ?? null;
    if (snapshotPosition !== graphState.lastSnapshotPosition) {
      const currentIds = new Set(nodes.map((node) => Number(node.id)));
      let added = 0;
      currentIds.forEach((id) => {
        if (!lastVisibleIds.has(id)) added += 1;
      });
      graphState.recentNewNodeCount = lastVisibleIds.size ? added : 0;
      lastVisibleIds = currentIds;
      graphState.lastSnapshotPosition = snapshotPosition;
    }
    if (!graphState.drag.active && graphState.focusNodeId === null && currentTimelineProgress() >= 0.995) {
      graphState.view.rotY += 0.00075;
      graphState.view.rotX = -0.24 + Math.sin(animationClock * 0.00024) * 0.035;
    }
    updateNodeLayout(nodes, rect.width, rect.height);
    graphState.visibleNodes = nodes;
    graphState.visibleEdges = edges;
    const visible = new Set(nodes.map((node) => Number(node.id)));
    const cx = rect.width * 0.5;
    const cy = rect.height * 0.5;

    const gradient = ctx.createRadialGradient(cx, rect.height * 0.45, 0, cx, cy, Math.min(rect.width, rect.height) * 0.72);
    gradient.addColorStop(0, "rgba(72,165,141,0.18)");
    gradient.addColorStop(1, "rgba(18,26,27,0)");
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, rect.width, rect.height);

    edges.forEach((edge) => {
      const source = Number(edge.source);
      const target = Number(edge.target);
      if (!visible.has(source) || !visible.has(target)) return;
      const a = graphState.nodes.get(source) || graphState.nodes.get(edge.source);
      const b = graphState.nodes.get(target) || graphState.nodes.get(edge.target);
      if (!a || !b) return;
      const risky = edge.riskLevel === "critical" || edge.riskLevel === "high";
      const medium = edge.riskLevel === "medium";
      const selectedPath = edgeInSelectedPath(edge);
      const focusPath = edgeTouchesFocus(edge);
      const kind = edgePathKind(edge, selectedEvent());
      const depthAlpha = Math.max(0.18, Math.min(0.72, (a.alpha + b.alpha) * 0.5));
      const [fromColor, toColor] = pathStrokeStyle(kind, selectedPath, focusPath, risky, medium, depthAlpha);
      const lineGradient = ctx.createLinearGradient(a.x, a.y, b.x, b.y);
      lineGradient.addColorStop(0, fromColor);
      lineGradient.addColorStop(1, toColor);
      ctx.strokeStyle = lineGradient;
      ctx.lineWidth = selectedPath ? 2.4 : focusPath ? 1.7 : edge.riskLevel === "critical" ? 1.15 : risky ? 0.92 : medium ? 0.64 : 0.46;
      if ((selectedPath || focusPath) && kind !== "fund") {
        ctx.setLineDash(kind === "device" ? [8, 5] : kind === "ip" ? [3, 5] : [10, 4, 3, 4]);
      } else {
        ctx.setLineDash([]);
      }
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.stroke();
      ctx.setLineDash([]);
    });

    const projectedNodes = [...nodes]
      .map((node) => ({ node, point: graphState.nodes.get(Number(node.id)) }))
      .filter((item) => item.point)
      .sort((a, b) => b.point.depth - a.point.depth);
    const rankedNodes = [...nodes].sort((a, b) => b.riskScore - a.riskScore);

    projectedNodes.forEach(({ node, point }) => {
      const color = nodeColor(node);
      const currentEvent = selectedEvent();
      const selectedIds = new Set((currentEvent?.relatedNodes || []).map((id) => Number(id)));
      const selectedNode = selectedIds.has(Number(node.id)) || Number(node.id) === Number(graphState.focusNodeId);
      const riskWeight = Math.max(0, Math.min(1, node.riskScore));
      const age = Math.min(1, (animationClock - (point.bornAt || animationClock)) / 900);
      const entryScale = 0.48 + age * 0.52;
      const entryPulse = Math.max(0, 1 - (animationClock - (point.bornAt || animationClock)) / 1500);
      const levelBoost = node.riskLevel === "critical" ? 1.55 : node.riskLevel === "high" ? 1.35 : node.riskLevel === "medium" ? 1.12 : 0.68;
      const baseRadius = 1.05 + Math.min(node.degree, 28) * 0.035 + Math.pow(riskWeight, 1.55) * 7.4;
      const radius = baseRadius * levelBoost * Math.max(0.46, point.perspective * 1.56) * entryScale;
      const nodeAlpha = Math.min(1, Math.max(0.12, point.alpha * (0.24 + riskWeight * 0.86)));
      const shadowBlur = node.riskLevel === "critical" ? 30 : node.riskLevel === "high" ? 24 : node.riskLevel === "medium" ? 14 : 3;
      if (entryPulse > 0) {
        ctx.beginPath();
        ctx.globalAlpha = entryPulse * 0.72;
        ctx.strokeStyle = color;
        ctx.lineWidth = 1.5 + entryPulse * 2.2;
        ctx.shadowColor = color;
        ctx.shadowBlur = 20 + entryPulse * 22;
        ctx.arc(point.x, point.y, radius + 9 + (1 - entryPulse) * 22, 0, Math.PI * 2);
        ctx.stroke();
        ctx.globalAlpha = 1;
        ctx.shadowBlur = 0;
      }
      ctx.beginPath();
      ctx.fillStyle = color;
      ctx.shadowColor = color;
      ctx.shadowBlur = shadowBlur;
      ctx.globalAlpha = nodeAlpha;
      ctx.arc(point.x, point.y, radius, 0, Math.PI * 2);
      ctx.fill();
      ctx.globalAlpha = 1;
      ctx.shadowBlur = 0;
      ctx.lineWidth = node.detectedFraud ? 1.9 : node.riskLevel === "medium" ? 1.1 : 0.45;
      ctx.strokeStyle = selectedNode ? "rgba(255,213,112,0.95)" : node.detectedFraud ? "rgba(255,253,246,0.86)" : node.riskLevel === "medium" ? "rgba(255,253,246,0.46)" : "rgba(255,253,246,0.18)";
      ctx.lineWidth = selectedNode ? Math.max(ctx.lineWidth, 2.4) : ctx.lineWidth;
      ctx.stroke();
      point.drawRadius = radius;
    });

    const labelLimit = graphState.view.zoom > 1.7 ? 16 : graphState.view.zoom > 1.25 ? 10 : 6;
    const labelMinimumScore = graphState.view.zoom > 1.7 ? 0.24 : graphState.view.zoom > 1.25 ? 0.30 : 0.35;
    rankedNodes.slice(0, labelLimit).forEach((node) => {
      const point = graphState.nodes.get(Number(node.id));
      if (!point || node.riskScore < labelMinimumScore) return;
      const label = `${node.id}  ${formatScore(node.riskScore)}`;
      ctx.font = "12px Times New Roman, Times, serif";
      const labelWidth = ctx.measureText(label).width + 14;
      const x = Math.min(Math.max(point.x + 10, 8), rect.width - labelWidth - 8);
      const y = Math.min(Math.max(point.y - 24, 8), rect.height - 28);
      ctx.fillStyle = "rgba(18,26,27,0.76)";
      ctx.strokeStyle = "rgba(255,253,246,0.16)";
      ctx.lineWidth = 1;
      ctx.beginPath();
      roundedRect(ctx, x, y, labelWidth, 22, 8);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = node.detectedFraud ? "#ffd4cf" : "#e6f3ec";
      ctx.fillText(label, x + 7, y + 15);
    });

    graphState.frameId = requestAnimationFrame(drawGraph);
  }

  function setupGraphInteractions() {
    const canvas = canvasRef.value;
    if (!canvas) return;
    canvas.addEventListener("pointerdown", onPointerDown);
    canvas.addEventListener("pointermove", onPointerMove);
    canvas.addEventListener("pointerup", endDrag);
    canvas.addEventListener("pointercancel", endDrag);
    canvas.addEventListener("wheel", onWheel, { passive: false });
    canvas.addEventListener("dblclick", resetView);
  }

  function removeGraphInteractions() {
    const canvas = canvasRef.value;
    if (!canvas) return;
    canvas.removeEventListener("pointerdown", onPointerDown);
    canvas.removeEventListener("pointermove", onPointerMove);
    canvas.removeEventListener("pointerup", endDrag);
    canvas.removeEventListener("pointercancel", endDrag);
    canvas.removeEventListener("wheel", onWheel);
    canvas.removeEventListener("dblclick", resetView);
  }

  function onPointerDown(event) {
    const canvas = canvasRef.value;
    graphState.drag.active = true;
    graphState.drag.pointerId = event.pointerId;
    graphState.drag.startX = event.clientX;
    graphState.drag.startY = event.clientY;
    graphState.drag.originRotX = graphState.view.rotX;
    graphState.drag.originRotY = graphState.view.rotY;
    graphState.drag.moved = false;
    canvas.classList.add("dragging");
    canvas.setPointerCapture(event.pointerId);
  }

  function onPointerMove(event) {
    if (!graphState.drag.active || graphState.drag.pointerId !== event.pointerId) return;
    const deltaX = event.clientX - graphState.drag.startX;
    const deltaY = event.clientY - graphState.drag.startY;
    if (Math.hypot(deltaX, deltaY) > 5) {
      graphState.drag.moved = true;
    }
    graphState.view.rotY = graphState.drag.originRotY + deltaX * 0.008;
    graphState.view.rotX = Math.max(-1.15, Math.min(1.15, graphState.drag.originRotX + deltaY * 0.006));
  }

  function endDrag(event) {
    const canvas = canvasRef.value;
    if (!graphState.drag.active || graphState.drag.pointerId !== event.pointerId) return;
    const shouldPick = !graphState.drag.moved;
    graphState.drag.active = false;
    graphState.drag.pointerId = null;
    canvas.classList.remove("dragging");
    try {
      canvas.releasePointerCapture(event.pointerId);
    } catch {
      // 浏览器可能已经释放指针。
    }
    if (shouldPick) {
      const node = pickNode(event.clientX, event.clientY);
      if (node) {
        focusNode(node);
      } else {
        clearFocus();
      }
    }
  }

  function onWheel(event) {
    event.preventDefault();
    const nextZoom = graphState.view.zoom * (event.deltaY > 0 ? 0.92 : 1.08);
    graphState.view.zoom = Math.max(0.52, Math.min(2.8, nextZoom));
  }

  function resetView() {
    graphState.view.rotX = -0.24;
    graphState.view.rotY = 0.58;
    graphState.view.zoom = 1.16;
    clearFocus();
  }

  onMounted(() => {
    setupGraphInteractions();
    drawGraph();
  });

  onBeforeUnmount(() => {
    removeGraphInteractions();
    if (graphState.frameId !== null) {
      cancelAnimationFrame(graphState.frameId);
    }
  });

  function clearFocus(shouldEmit = true) {
    graphState.focusNodeId = null;
    graphState.focusMode = "screen";
    graphState.focusLoading = false;
    graphState.focusError = "";
    graphState.neighborhood = null;
    graphState.focusNeighborCount = 0;
    graphState.focusEdgeCount = 0;
    if (shouldEmit && emitFocusChange) emitFocusChange(null);
  }

  return { graphState, clearFocus, focusNodeById };
}
