<script setup>
import { computed, ref, watch } from "vue";
import { useGraphCanvas } from "../composables/useGraphCanvas";
import {
  actionLabel,
  communityLabel,
  evidenceValueLabel,
  formatNumber,
  formatReadableTime,
  formatScore,
  graphFilterLabel,
  reasonLabel,
  riskLabel,
} from "../utils/format";

const props = defineProps({
  snapshot: { type: Object, default: null },
  replayToken: { type: Number, default: 0 },
  focusNodeId: { type: [Number, String], default: null },
  filterMode: { type: String, default: "all" },
  legendState: {
    type: Object,
    default: () => ({ normal: true, review: true, fraud: true, related: true }),
  },
  selectedEvent: { type: Object, default: null },
  paused: { type: Boolean, default: false },
  speed: { type: Number, default: 1 },
  compact: { type: Boolean, default: false },
  graphMode: { type: String, default: "window" },
});

const emit = defineEmits(["focus-change", "update:filterMode", "update:legendState", "toggle-pause", "speed-change", "replay"]);

const canvasRef = ref(null);
const snapshotRef = computed(() => props.snapshot);
const replayTokenRef = computed(() => props.replayToken);
const focusNodeIdRef = computed(() => props.focusNodeId);
const filterModeRef = computed(() => props.filterMode);
const legendStateRef = computed(() => props.legendState);
const selectedEventRef = computed(() => props.selectedEvent);
const graphModeRef = computed(() => props.graphMode);
const meta = computed(() => props.snapshot?.meta ?? {});
const progress = computed(() => Number(meta.value.progress || 0));
const searchText = ref("");
const localProgress = ref(0);
const manualProgress = ref(null);
const timelineProgress = computed(() => manualProgress.value ?? progress.value);
const timelineProgressRef = computed(() => timelineProgress.value);
const nodeCountLabel = computed(() => (props.graphMode === "cumulative" ? "累计节点" : "当前窗口节点"));
const { graphState, clearFocus } = useGraphCanvas(canvasRef, snapshotRef, replayTokenRef, {
  focusNodeIdRef,
  filterModeRef,
  legendStateRef,
  selectedEventRef,
  graphModeRef,
  timelineProgressRef,
  onFocusChange: (nodeId) => emit("focus-change", nodeId),
});

const filterOptions = [
  { id: "all" },
  { id: "high" },
  { id: "community" },
  { id: "device_reuse" },
  { id: "ip_cluster" },
  { id: "merchant_laundering" },
];
const legendOptions = [
  { id: "normal", label: "正常节点", color: "#45b591" },
  { id: "review", label: "待复核节点", color: "#d18b24" },
  { id: "fraud", label: "疑似欺诈节点", color: "#d94b42" },
  { id: "related", label: "关系连线", color: "#8fa0a0" },
];

const activeNode = computed(() => {
  const nodeId = graphState.focusNodeId;
  if (nodeId === null || nodeId === undefined) return null;
  const nodes = [
    ...(graphState.visibleNodes || []),
    ...(props.snapshot?.nodes || []),
    ...(graphState.neighborhood?.nodes || []),
  ];
  return nodes.find((node) => Number(node.id) === Number(nodeId)) || { id: nodeId };
});

const nodeEvent = computed(() => {
  if (props.selectedEvent) return props.selectedEvent;
  const nodeId = Number(graphState.focusNodeId);
  if (!Number.isFinite(nodeId)) return props.snapshot?.lastEvent || null;
  return (props.snapshot?.recentEvents || []).find((event) => {
    const related = new Set((event.relatedNodes || []).map((id) => Number(id)));
    return Number(event.focusNode) === nodeId || Number(event.srcNode) === nodeId || Number(event.dstNode) === nodeId || related.has(nodeId);
  }) || props.snapshot?.lastEvent || null;
});

const detailRows = computed(() => {
  const node = activeNode.value;
  const event = nodeEvent.value || {};
  const evidence = event.evidence || {};
  if (!node) return [];
  return [
    { label: "风险等级", value: riskLabel(node.riskLevel || event.riskLevel) },
    { label: "风险分", value: formatScore(node.riskScore ?? event.riskScore) },
    { label: "处置建议", value: actionLabel(node.action || event.action) },
    { label: "最近交易", value: event.amount ? `${Number(event.amount).toFixed(2)} 元` : "暂无" },
    { label: "共用设备", value: evidenceValueLabel("device_account_count", evidence.device_account_count) },
    { label: "同 IP 账户", value: evidenceValueLabel("ip_account_count", evidence.ip_account_count) },
    { label: "团伙编号", value: communityLabel(event.communityId || evidence.graph_community_id) },
    { label: "相关邻居", value: evidenceValueLabel("graph_neighbor_count", evidence.graph_neighbor_count ?? graphState.focusNeighborCount) },
  ];
});

const reasonItems = computed(() => {
  const codes = nodeEvent.value?.reasonCodes || [];
  return codes.length ? codes.map(reasonLabel) : ["模型评分命中"];
});

const relatedNodes = computed(() => {
  const nodes = nodeEvent.value?.relatedNodes || [];
  if (nodes.length) return nodes.slice(0, 12);
  return (graphState.visibleNodes || []).map((node) => node.id).filter((id) => Number(id) !== Number(graphState.focusNodeId)).slice(0, 12);
});

watch(progress, (nextProgress) => {
  localProgress.value = Math.round(Number(nextProgress || 0) * 1000);
  if (!props.paused) manualProgress.value = null;
}, { immediate: true });

function setFilter(mode) {
  emit("update:filterMode", mode);
}

function toggleLegend(key) {
  emit("update:legendState", {
    ...props.legendState,
    [key]: props.legendState[key] === false,
  });
}

function searchNode() {
  const query = searchText.value.trim();
  if (!query) return;
  const normalizedQuery = query.toLowerCase();
  const matchedEvent = (props.snapshot?.recentEvents || []).find((event) => {
    const evidence = event.evidence || {};
    const values = [
      event.srcNode,
      event.dstNode,
      event.focusNode,
      evidence.src_account,
      evidence.dst_account,
      evidence.device_id,
      evidence.ip,
      evidence.merchant_id,
      evidence.graph_community_id,
    ];
    return values.some((value) => String(value ?? "").toLowerCase().includes(normalizedQuery));
  });
  const normalized = matchedEvent?.focusNode ?? matchedEvent?.srcNode ?? Number(query.replace(/[^\d]/g, ""));
  if (!Number.isFinite(normalized)) return;
  if (matchedEvent) emit("update:filterMode", "community");
  emit("focus-change", normalized);
}

function changeSpeed(nextSpeed) {
  emit("speed-change", nextSpeed);
}

function togglePlayback() {
  emit("toggle-pause", !props.paused);
}

function seekTimeline(value) {
  localProgress.value = Number(value);
  manualProgress.value = Number(value) / 1000;
  emit("toggle-pause", true);
}

function resumeLatest() {
  manualProgress.value = null;
  emit("toggle-pause", false);
}
</script>

<template>
  <section class="graph-panel" aria-label="团伙关系追溯图">
    <div class="graph-toolbar">
      <div class="filter-group" aria-label="图谱筛选">
        <button
          v-for="item in filterOptions"
          :key="item.id"
          type="button"
          class="filter-button"
          :class="{ active: filterMode === item.id }"
          @click="setFilter(item.id)"
        >
          {{ graphFilterLabel(item.id) }}
        </button>
      </div>
      <div class="graph-counts">
        <span>{{ nodeCountLabel }} {{ formatNumber(graphState.visibleNodes.length) }}</span>
        <span>关系 {{ formatNumber(graphState.visibleEdges.length) }}</span>
        <span v-if="graphState.recentNewNodeCount > 0" class="new-node-count">新进入 {{ formatNumber(graphState.recentNewNodeCount) }}</span>
      </div>
    </div>
    <form v-if="!compact" class="graph-search" @submit.prevent="searchNode">
      <input v-model="searchText" type="search" inputmode="numeric" placeholder="搜索账户、设备、IP、商户编号" aria-label="搜索节点" />
      <button type="submit">定位</button>
    </form>
    <canvas id="graph-canvas" ref="canvasRef"></canvas>
    <div v-if="graphState.focusNodeId !== null" class="focus-badge">
      <span>已聚焦节点 <b class="latin-number">{{ graphState.focusNodeId }}</b></span>
      <span v-if="graphState.focusLoading">正在查询完整邻域</span>
      <span v-else>完整邻域 {{ graphState.focusNeighborCount }} 个相关节点 / {{ graphState.focusEdgeCount }} 条关系</span>
      <span v-if="graphState.focusError">{{ graphState.focusError }}</span>
      <button type="button" @click="clearFocus">恢复全图</button>
    </div>
    <aside v-if="activeNode && !compact" class="graph-detail-drawer" aria-label="节点风险详情">
      <div class="drawer-head">
        <span>节点详情</span>
        <strong>账户 <b class="latin-number">{{ activeNode.id }}</b></strong>
      </div>
      <div class="drawer-score">
        <span>{{ riskLabel(activeNode.riskLevel || nodeEvent?.riskLevel) }}</span>
        <strong class="latin-number">{{ formatScore(activeNode.riskScore ?? nodeEvent?.riskScore) }}</strong>
      </div>
      <div class="detail-grid">
        <div v-for="row in detailRows" :key="row.label" class="detail-item">
          <span>{{ row.label }}</span>
          <strong>{{ row.value }}</strong>
        </div>
      </div>
      <div class="drawer-section">
        <h3>命中原因</h3>
        <span v-for="reason in reasonItems" :key="reason" class="reason-pill">{{ reason }}</span>
      </div>
      <div class="drawer-section">
        <h3>相关节点</h3>
        <div class="related-node-list">
          <span v-for="nodeId in relatedNodes" :key="nodeId" class="latin-number">{{ nodeId }}</span>
          <span v-if="relatedNodes.length === 0">暂无</span>
        </div>
      </div>
      <div class="drawer-section path-legend">
        <h3>路径类型</h3>
        <span><i style="--line:#fffdf6"></i>资金路径</span>
        <span><i style="--line:#58a6ff"></i>共同设备</span>
        <span><i style="--line:#b784ff"></i>共同 IP</span>
        <span><i style="--line:#ffaf52"></i>商户关系</span>
      </div>
    </aside>
    <div class="graph-overlay">
      <div class="legend">
        <button
          v-for="item in legendOptions"
          :key="item.id"
          type="button"
          class="legend-item"
          :class="{ inactive: legendState[item.id] === false }"
          @click="toggleLegend(item.id)"
        >
          <i class="dot" :style="{ '--color': item.color }"></i>{{ item.label }}
        </button>
      </div>
      <div class="progress">
        <div class="progress-head">
          <span id="progress-label">{{ formatNumber(meta.position) }} / {{ formatNumber(meta.totalEvents) }}</span>
          <span id="timestamp-label">{{ formatReadableTime(meta.currentTimestamp) }}</span>
        </div>
        <input v-if="!compact" class="timeline-range" type="range" min="0" max="1000" :value="localProgress" aria-label="回放时间轴" @input="seekTimeline($event.target.value)" />
        <div v-if="!compact" class="timeline-actions">
          <button type="button" @click="togglePlayback">{{ paused ? "继续" : "暂停" }}</button>
          <button type="button" :class="{ active: speed === 1 }" @click="changeSpeed(1)">1 倍</button>
          <button type="button" :class="{ active: speed === 2 }" @click="changeSpeed(2)">2 倍</button>
          <button type="button" @click="resumeLatest">回到最新</button>
          <button type="button" @click="emit('replay')">重放</button>
        </div>
        <div class="track" :style="{ '--progress': timelineProgress }"><i id="progress-bar"></i></div>
      </div>
    </div>
  </section>
</template>
