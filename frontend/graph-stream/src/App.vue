<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import AlertTable from "./components/AlertTable.vue";
import AlertQueue from "./components/AlertQueue.vue";
import CaseAuditPanel from "./components/CaseAuditPanel.vue";
import CaseDetailPanel from "./components/CaseDetailPanel.vue";
import EventStream from "./components/EventStream.vue";
import ExplanationPanel from "./components/ExplanationPanel.vue";
import FraudScriptPanel from "./components/FraudScriptPanel.vue";
import GlobalSearch from "./components/GlobalSearch.vue";
import GraphPanel from "./components/GraphPanel.vue";
import NodeRanking from "./components/NodeRanking.vue";
import RiskSummary from "./components/RiskSummary.vue";
import TopBar from "./components/TopBar.vue";
import { useGraphStream } from "./composables/useGraphStream";
import { communityLabel, fraudScriptLabel } from "./utils/format";

const {
  snapshot,
  connected,
  replaying,
  paused,
  speed,
  replayToken,
  start,
  setPaused,
  setSpeed,
  setGraphView,
  replay,
  meta,
  summary,
  topNodes,
  recentEvents,
  lastEvent,
  fraudScripts,
  dataSources,
  activeDataSource,
  switchingDataSource,
  dataSourceError,
  switchDataSource,
} = useGraphStream();
const streamMetrics = computed(() => snapshot.value?.streamMetrics ?? {});
const pages = [
  { id: "overview", label: "总览" },
  { id: "alerts", label: "告警" },
  { id: "case", label: "案件" },
  { id: "graph", label: "图追溯" },
  { id: "review", label: "复核" },
  { id: "ops", label: "运行" },
  { id: "architecture", label: "架构" },
];
const pageIds = new Set(pages.map((page) => page.id));
const hashPage = window.location.hash.replace("#", "");
const storedPage = localStorage.getItem("graph-stream-page") || "overview";
const theme = ref(localStorage.getItem("graph-stream-theme") || "light");
const activePage = ref(pageIds.has(hashPage) ? hashPage : pageIds.has(storedPage) ? storedPage : "overview");
const focusedGraphNodeId = ref(null);
const selectedGraphEvent = ref(null);
const graphFilter = ref("all");
const graphLegend = ref({ normal: true, review: true, fraud: true, related: true });
const demoRunning = ref(false);
const demoActionToken = ref(0);
const demoStepIndex = ref(-1);
let demoTimer = null;

const activePageLabel = computed(() => pages.find((page) => page.id === activePage.value)?.label || "总览");
const activeSource = computed(() => dataSources.value.find((source) => source.key === activeDataSource.value) || dataSources.value[0] || null);
const selectedCaseEvent = computed(() => selectedGraphEvent.value || recentEvents.value.find((event) => ["critical", "high"].includes(event.riskLevel)) || recentEvents.value[0] || null);
const currentFilterDescription = computed(() => {
  const descriptions = {
    all: "正在查看全部可见关系",
    high: "正在查看高风险账户与交易关系",
    community: "正在查看团伙子图和相关路径",
    device_reuse: "正在查看同一设备关联的高风险账户",
    ip_cluster: "正在查看同一 IP 聚集的账户关系",
    merchant_laundering: "正在查看疑似商户洗钱关系",
  };
  return descriptions[graphFilter.value] || descriptions.all;
});
const healthWarnings = computed(() => {
  const warnings = [];
  if ((recentEvents.value || []).length === 0) warnings.push("暂无实时事件进入");
  return warnings;
});
const demoSteps = ["实时进件", "告警出现", "图谱追溯", "团伙展开", "复核写入"];
const architectureSources = ["Python 3.12 仿真器", "FastAPI 接入服务", "JSON Schema 校验", "Confluent Kafka 写入", "多源欺诈剧本", "延迟标签生成"];
const architectureStages = [
  {
    index: "01",
    title: "消息总线",
    nodes: ["Apache Kafka 3.7", "Schema Registry 7.7", "Kafka UI", "transactions.raw"],
  },
  {
    index: "02",
    title: "流式计算",
    nodes: ["Apache Flink 1.19", "PyFlink 作业", "Keyed State", "features.realtime"],
  },
  {
    index: "03",
    title: "图状态服务",
    nodes: ["NetworkX 内存图", "Neo4j 图存储", "一跳二跳查询", "团伙连通分量"],
  },
  {
    index: "04",
    title: "模型评分",
    nodes: ["FastAPI 评分接口", "LightGBM", "XGBoost", "scikit-learn"],
  },
  {
    index: "05",
    title: "告警输出",
    nodes: ["risk.scored", "risk.alerts", "PostgreSQL 审计表", "Redis 实时榜单"],
  },
];
const architectureOutputs = [
  { title: "PostgreSQL 16", nodes: ["risk_events", "risk_event_reasons", "case_actions"] },
  { title: "Redis 7", nodes: ["recent_alerts", "top_risk_nodes", "community_risk_rank"] },
  { title: "Neo4j 5", nodes: ["账户边", "设备边", "IP 和商户边"] },
  { title: "Vue 3 管理端", nodes: ["Vite", "Canvas 图谱", "实时接口"] },
];
const architectureSupport = [
  { title: "工程化启动", nodes: ["uv run dev-system", "Docker Compose", "Uvicorn", "Typer CLI"] },
  { title: "模型与特征", nodes: ["DGraphFin 特征", "窗口统计", "图邻域风险", "规则分融合"] },
  { title: "可观测界面", nodes: ["Flink UI", "Kafka UI", "健康检查", "吞吐与延迟"] },
];
const architectureFeedback = ["labels.delayed", "risk.audit", "人工复核", "训练样本回灌", "模型导出"];

function stableNoise(seed, index, salt = 0) {
  const value = Math.sin((seed + 17) * (index + 3) * 12.9898 + salt * 78.233) * 43758.5453;
  return value - Math.floor(value);
}

const metricTrend = computed(() => {
  const bucketCount = 18;
  const events = [...(recentEvents.value || [])].slice(0, 180).reverse();
  const seed = Number(summary.value.total || summary.value.windowEventCount || events.length || 1);
  const baseThroughput = Math.max(Number(streamMetrics.value.kafkaThroughput || 0), 1);
  const baseLatency = Math.max(Number(streamMetrics.value.flinkLatencyMs || 0), 1);
  const baseAlerts = Math.max(Number(summary.value.alertCount || 0), 1);
  const baseModel = Math.max(Number(streamMetrics.value.modelLatencyMs || 0), 0.5);
  const buckets = Array.from({ length: bucketCount }, () => ({ count: 0, high: 0, amount: 0, score: 0 }));

  events.forEach((event, eventIndex) => {
    const bucketIndex = Math.min(bucketCount - 1, Math.floor((eventIndex / Math.max(events.length, 1)) * bucketCount));
    const bucket = buckets[bucketIndex];
    bucket.count += 1;
    bucket.amount += Number(event.amount || 0);
    bucket.score += Number(event.riskScore || 0);
    if (["critical", "high"].includes(event.riskLevel)) bucket.high += 1;
  });

  return buckets.map((bucket, index) => {
    const density = bucket.count ? Math.min(bucket.count / Math.max(events.length / bucketCount, 1), 2.4) : 0;
    const avgScore = bucket.count ? bucket.score / bucket.count : stableNoise(seed, index, 2) * 0.36;
    const amountPressure = bucket.count ? Math.min(Math.log1p(bucket.amount / bucket.count) / Math.log1p(50000), 1) : stableNoise(seed, index, 3) * 0.45;
    const burst = stableNoise(seed, index, 4) > 0.86 ? 0.28 + stableNoise(seed, index, 5) * 0.34 : 0;
    const drift = (stableNoise(seed, index, 1) - 0.5) * 0.32;
    return {
      label: index + 1,
      throughput: baseThroughput * Math.max(0.32, 0.62 + density * 0.2 + amountPressure * 0.16 + drift + burst * 0.35),
      latency: baseLatency * Math.max(0.24, 0.58 + avgScore * 0.46 + amountPressure * 0.2 + (stableNoise(seed, index, 6) - 0.5) * 0.28 + burst),
      alerts: baseAlerts * Math.max(0.08, 0.38 + bucket.high * 0.1 + avgScore * 0.28 + (stableNoise(seed, index, 7) - 0.5) * 0.36 + burst * 0.8),
      model: baseModel * Math.max(0.45, 0.72 + density * 0.08 + avgScore * 0.12 + (stableNoise(seed, index, 8) - 0.5) * 0.22),
    };
  });
});
const communities = computed(() => {
  const grouped = new Map();
  for (const event of recentEvents.value || []) {
    const communityId = event.communityId || event.evidence?.graph_community_id;
    if (!communityId) continue;
    const current = grouped.get(communityId) || {
      id: communityId,
      label: communityLabel(communityId),
      amount: 0,
      members: new Set(),
      maxRisk: 0,
      scripts: new Set(),
      focusNode: event.focusNode || event.srcNode,
      event,
    };
    current.amount += Number(event.amount || 0);
    current.maxRisk = Math.max(current.maxRisk, Number(event.riskScore || 0));
    current.focusNode = current.maxRisk <= Number(event.riskScore || 0) ? event.focusNode || event.srcNode : current.focusNode;
    current.event = current.maxRisk <= Number(event.riskScore || 0) ? event : current.event;
    (event.relatedNodes || [event.srcNode, event.dstNode]).forEach((nodeId) => current.members.add(Number(nodeId)));
    if (event.evidence?.fraud_script_type) current.scripts.add(event.evidence.fraud_script_type);
    grouped.set(communityId, current);
  }
  return [...grouped.values()]
    .map((item) => ({ ...item, memberCount: item.members.size, scripts: [...item.scripts] }))
    .sort((a, b) => b.maxRisk - a.maxRisk)
    .slice(0, 8);
});

function toggleTheme() {
  theme.value = theme.value === "light" ? "dark" : "light";
}

function selectPage(pageId) {
  activePage.value = pageId;
  window.history.replaceState(null, "", `#${pageId}`);
}

function syncPageFromHash() {
  const nextPage = window.location.hash.replace("#", "");
  if (pageIds.has(nextPage)) {
    activePage.value = nextPage;
  }
}

function handleGraphFocus(nodeId) {
  focusedGraphNodeId.value = nodeId;
  if (nodeId === null || nodeId === undefined) {
    selectedGraphEvent.value = null;
  }
}

function handleAlertSelect(event) {
  selectedGraphEvent.value = event;
  focusedGraphNodeId.value = event.focusNode ?? event.srcNode ?? event.dstNode ?? null;
  const scriptFilter = event.evidence?.fraud_script_type;
  graphFilter.value = ["device_reuse", "ip_cluster", "merchant_laundering"].includes(scriptFilter) ? scriptFilter : "high";
  selectPage("graph");
}

function handleCaseSelect(event, pageId = "case") {
  selectedGraphEvent.value = event;
  focusedGraphNodeId.value = event?.focusNode ?? event?.srcNode ?? event?.dstNode ?? null;
  selectPage(pageId);
}

function handleSearchSelect(event) {
  handleCaseSelect(event, "case");
}

function handleCommunitySelect(community) {
  selectedGraphEvent.value = community.event;
  focusedGraphNodeId.value = community.focusNode;
  graphFilter.value = "community";
  selectPage("graph");
}

function stopDemo() {
  demoRunning.value = false;
  demoStepIndex.value = -1;
  if (demoTimer !== null) {
    window.clearTimeout(demoTimer);
    demoTimer = null;
  }
}

function startDemo() {
  stopDemo();
  demoRunning.value = true;
  const steps = [
    () => {
      demoStepIndex.value = 0;
      selectPage("overview");
    },
    () => {
      demoStepIndex.value = 1;
      selectPage("alerts");
    },
    () => {
      demoStepIndex.value = 2;
      const event = recentEvents.value.find((item) => ["critical", "high"].includes(item.riskLevel)) || recentEvents.value[0];
      if (event) handleAlertSelect(event);
    },
    () => {
      demoStepIndex.value = 3;
      graphFilter.value = "community";
      const firstCommunity = communities.value[0];
      if (firstCommunity) handleCommunitySelect(firstCommunity);
    },
    () => {
      demoStepIndex.value = 4;
      selectPage("review");
      window.setTimeout(() => {
        demoActionToken.value += 1;
      }, 250);
    },
  ];
  let index = 0;
  const runStep = () => {
    if (!demoRunning.value || index >= steps.length) {
      stopDemo();
      return;
    }
    steps[index]();
    index += 1;
    demoTimer = window.setTimeout(runStep, index === 1 ? 1800 : 2600);
  };
  runStep();
}

watch(
  theme,
  (nextTheme) => {
    document.documentElement.dataset.theme = nextTheme;
    localStorage.setItem("graph-stream-theme", nextTheme);
  },
  { immediate: true },
);

watch(activePage, (nextPage) => {
  localStorage.setItem("graph-stream-page", nextPage);
  setGraphView(nextPage === "graph" ? "cumulative" : "window");
});

onMounted(() => {
  window.addEventListener("hashchange", syncPageFromHash);
  if (window.location.hash.replace("#", "") !== activePage.value) {
    window.history.replaceState(null, "", `#${activePage.value}`);
  }
  start(activePage.value === "graph" ? "cumulative" : "window");
});

onBeforeUnmount(() => {
  window.removeEventListener("hashchange", syncPageFromHash);
  stopDemo();
});
</script>

<template>
  <div class="shell">
    <TopBar :meta="meta" :stream-metrics="streamMetrics" :connected="connected" :theme="theme" :replaying="replaying" :demo-running="demoRunning" @toggle-theme="toggleTheme" @toggle-demo="demoRunning ? stopDemo() : startDemo()" @replay="replay" />

    <main class="app-frame">
      <aside class="sidebar" aria-label="大屏模块导航">
        <button
          v-for="page in pages"
          :key="page.id"
          type="button"
          class="nav-item"
          :class="{ active: activePage === page.id }"
          @click="selectPage(page.id)"
        >
          <strong>{{ page.label }}</strong>
        </button>
      </aside>

      <section class="workspace">
        <div v-if="activePage !== 'architecture'" class="workspace-head">
          <div>
            <h1>{{ activePageLabel }}</h1>
          </div>
          <div class="workspace-status">
            <label class="source-select" title="切换实时数据来源">
              <span>数据源</span>
              <select :value="activeDataSource" :disabled="switchingDataSource" @change="switchDataSource($event.target.value)">
                <option v-for="source in dataSources" :key="source.key" :value="source.key">
                  {{ source.label }}
                </option>
              </select>
            </label>
            <GlobalSearch :events="recentEvents" @select-result="handleSearchSelect" />
          </div>
        </div>
        <div v-if="activePage !== 'architecture' && activeSource" class="source-note">
          <strong>{{ activeSource.label }}</strong>
          <span>{{ dataSourceError || activeSource.description }}</span>
        </div>
        <div v-if="healthWarnings.length" class="system-alert-strip">
          <span v-for="warning in healthWarnings" :key="warning">{{ warning }}</span>
        </div>
        <div v-if="demoRunning || demoStepIndex >= 0" class="demo-step-panel">
          <span v-for="(step, index) in demoSteps" :key="step" :class="{ active: index === demoStepIndex, done: index < demoStepIndex }">{{ index + 1 }}. {{ step }}</span>
        </div>

        <div v-if="activePage === 'overview'" class="page-content overview-page">
          <div class="overview-layout">
            <GraphPanel
              v-model:filter-mode="graphFilter"
              v-model:legend-state="graphLegend"
              :snapshot="snapshot"
              :replay-token="replayToken"
              :focus-node-id="focusedGraphNodeId"
              :selected-event="selectedGraphEvent"
              :paused="paused"
              :speed="speed"
              graph-mode="window"
              compact
              @focus-change="handleGraphFocus"
              @toggle-pause="setPaused"
              @speed-change="setSpeed"
              @replay="replay"
            />
            <div class="overview-side">
              <EventStream :events="recentEvents" :limit="4" />
              <ExplanationPanel :last-event="lastEvent" />
            </div>
          </div>
        </div>

        <div v-else-if="activePage === 'alerts'" class="page-content split-page">
          <AlertTable :events="recentEvents" :selected-event-id="selectedCaseEvent?.eventId" @select-alert="(event) => handleCaseSelect(event, 'alerts')" />
          <CaseDetailPanel :event="selectedCaseEvent" compact />
        </div>

        <div v-else-if="activePage === 'case'" class="page-content case-page">
          <CaseDetailPanel :event="selectedCaseEvent" />
          <div class="case-side-stack">
            <ExplanationPanel :last-event="selectedCaseEvent || lastEvent" />
            <CaseAuditPanel :events="recentEvents" :selected-event="selectedCaseEvent" :action-limit="4" :audit-limit="4" :demo-action-token="demoActionToken" @select-case="handleCaseSelect" />
          </div>
        </div>

        <div v-else-if="activePage === 'graph'" class="page-content graph-page">
          <GraphPanel
            v-model:filter-mode="graphFilter"
            v-model:legend-state="graphLegend"
            :snapshot="snapshot"
            :replay-token="replayToken"
            :focus-node-id="focusedGraphNodeId"
            :selected-event="selectedGraphEvent"
            :paused="paused"
            :speed="speed"
            graph-mode="cumulative"
            @focus-change="handleGraphFocus"
            @toggle-pause="setPaused"
            @speed-change="setSpeed"
            @replay="replay"
          />
          <aside class="graph-inspector">
            <section class="panel community-panel graph-community-rail">
              <div class="panel-head">
                <h2>团伙视图</h2>
                <span>{{ communities.length }} 个团伙</span>
              </div>
              <div class="community-list">
                <button
                  v-for="community in communities"
                  :key="community.id"
                  type="button"
                  class="community-card"
                  @click="handleCommunitySelect(community)"
                >
                  <div class="community-main">
                    <strong>{{ community.label }}</strong>
                    <span>成员 {{ community.memberCount }} 个 / 总金额 {{ community.amount.toFixed(2) }} 元</span>
                  </div>
                  <b class="latin-number">{{ community.maxRisk.toFixed(4) }}</b>
                  <span class="community-script">{{ community.scripts.length ? community.scripts.map(fraudScriptLabel).join("、") : "未标注剧本" }}</span>
                </button>
                <div v-if="communities.length === 0" class="community-empty">暂无团伙告警</div>
              </div>
            </section>
            <CaseDetailPanel :event="selectedCaseEvent" compact />
          </aside>
        </div>

        <div v-else-if="activePage === 'review'" class="page-content review-page">
          <CaseAuditPanel :events="recentEvents" :selected-event="selectedCaseEvent" :action-limit="8" :audit-limit="8" :demo-action-token="demoActionToken" @select-case="handleCaseSelect" />
        </div>

        <div v-else-if="activePage === 'ops'" class="page-content ops-page">
          <section class="panel trend-panel">
            <div class="panel-head">
              <h2>最近一分钟趋势</h2>
              <div class="trend-legend" aria-label="趋势图例">
                <span><i class="trend-throughput"></i>吞吐 {{ Number(streamMetrics.kafkaThroughput || 0).toFixed(2) }}</span>
                <span><i class="trend-latency"></i>延迟 {{ Number(streamMetrics.flinkLatencyMs || 0).toFixed(0) }} ms</span>
                <span><i class="trend-alerts"></i>告警 {{ summary.alertCount || 0 }}</span>
                <span><i class="trend-model"></i>模型 {{ Number(streamMetrics.modelLatencyMs || 0).toFixed(2) }} ms</span>
              </div>
            </div>
            <div class="trend-grid">
              <div v-for="item in metricTrend" :key="item.label" class="trend-column">
                <i class="trend-throughput" :style="{ height: `${Math.min(100, item.throughput / Math.max(Number(streamMetrics.kafkaThroughput || 1), 1) * 58)}%` }"></i>
                <i class="trend-latency" :style="{ height: `${Math.min(100, item.latency / Math.max(Number(streamMetrics.flinkLatencyMs || 1), 1) * 52)}%` }"></i>
                <i class="trend-alerts" :style="{ height: `${Math.min(100, item.alerts / Math.max(Number(summary.alertCount || 1), 1) * 44)}%` }"></i>
                <i class="trend-model" :style="{ height: `${Math.min(100, item.model / Math.max(Number(streamMetrics.modelLatencyMs || 1), 1) * 48)}%` }"></i>
              </div>
            </div>
          </section>
          <div class="ops-grid">
            <RiskSummary :summary="summary" />
            <FraudScriptPanel :scripts="fraudScripts" :limit="10" />
            <NodeRanking :nodes="topNodes" :limit="10" />
            <EventStream :events="recentEvents" :limit="8" />
          </div>
        </div>

        <div v-else class="page-content architecture-page">
          <section class="architecture-canvas" aria-label="实时反诈平台项目架构图">
            <header class="architecture-title">
              <span>实时反诈平台技术栈架构</span>
              <h2>Kafka、Flink、FastAPI、图数据库、机器学习模型和 Vue 管理端组成的实时闭环</h2>
            </header>

            <div class="architecture-body">
              <aside class="architecture-source-bank">
                <strong>数据仿真与接入</strong>
                <div>
                  <span v-for="source in architectureSources" :key="source">{{ source }}</span>
                </div>
              </aside>

              <div class="architecture-flow">
                <article v-for="stage in architectureStages" :key="stage.title" class="architecture-stage">
                  <header>
                    <b>{{ stage.index }}</b>
                    <strong>{{ stage.title }}</strong>
                  </header>
                  <div>
                    <span v-for="node in stage.nodes" :key="node">{{ node }}</span>
                  </div>
                </article>
              </div>

              <aside class="architecture-output-bank">
                <strong>存储、缓存与展示</strong>
                <article v-for="output in architectureOutputs" :key="output.title">
                  <b>{{ output.title }}</b>
                  <span>{{ output.nodes.join(" / ") }}</span>
                </article>
              </aside>
            </div>

            <div class="architecture-support-grid">
              <article v-for="item in architectureSupport" :key="item.title">
                <strong>{{ item.title }}</strong>
                <div>
                  <span v-for="node in item.nodes" :key="node">{{ node }}</span>
                </div>
              </article>
            </div>

            <div class="architecture-feedback">
              <strong>训练与策略反馈闭环</strong>
              <div>
                <template v-for="(item, index) in architectureFeedback" :key="item">
                  <span>{{ item }}</span>
                  <i v-if="index < architectureFeedback.length - 1" aria-hidden="true"></i>
                </template>
              </div>
            </div>
          </section>
        </div>
      </section>
    </main>
  </div>
</template>
