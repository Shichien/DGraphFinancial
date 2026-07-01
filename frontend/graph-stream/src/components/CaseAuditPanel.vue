<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { fetchAuditLogs, fetchCaseActions, recordCaseAction } from "../api/graphStream";
import { actionLabel, channelLabel, communityLabel, formatReadableDateTime, formatReadableTime, formatScore, riskLabel } from "../utils/format";

const props = defineProps({
  events: { type: Array, default: () => [] },
  selectedEvent: { type: Object, default: null },
  actionLimit: { type: Number, default: 8 },
  auditLimit: { type: Number, default: 8 },
  demoActionToken: { type: Number, default: 0 },
});

const emit = defineEmits(["select-case"]);

const auditLogs = ref([]);
const caseActions = ref([]);
const localCaseActions = ref([]);
const busyStatus = ref("");
const connected = ref(true);
const writeError = ref("");
let timer = null;

const queue = computed(() => props.events.filter((event) => ["critical", "high", "medium"].includes(event.riskLevel)).slice(0, 16));
const focusEvent = computed(() => props.selectedEvent || queue.value[0] || null);

const statusText = {
  pending_review: "待复核",
  confirmed_fraud: "确认欺诈",
  false_positive: "误报放行",
  manual_block: "人工冻结",
  released: "解除限制",
  auto_pass: "自动放行",
};

const auditText = {
  risk_decision_created: "风险判定",
  case_action_recorded: "人工处置",
};

const displayedCaseActions = computed(() => {
  const seen = new Set();
  return [...localCaseActions.value, ...caseActions.value].filter((item) => {
    const key = `${item.event_id}-${item.status}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
});

async function refreshAudit() {
  try {
    const [auditResult, caseResult] = await Promise.all([fetchAuditLogs({ limit: 24 }), fetchCaseActions({ limit: 24 })]);
    auditLogs.value = auditResult.logs || [];
    caseActions.value = caseResult.actions || [];
    connected.value = true;
  } catch {
    connected.value = false;
  }
}

async function submitAction(status) {
  if (!focusEvent.value || busyStatus.value) return;
  busyStatus.value = status;
  writeError.value = "";
  try {
    await recordCaseAction({
      eventId: focusEvent.value.eventId,
      status,
      reviewer: "realtime-console",
      note: `风险分 ${Number(focusEvent.value.riskScore || 0).toFixed(4)}`,
    });
    localCaseActions.value.unshift({
      case_id: `local-${focusEvent.value.eventId}-${Date.now()}`,
      event_id: focusEvent.value.eventId,
      status,
      updated_at: new Date().toISOString(),
    });
    localCaseActions.value = localCaseActions.value.slice(0, 5);
    await refreshAudit();
  } catch {
    writeError.value = "处置写入失败，请检查风险事件库";
  } finally {
    busyStatus.value = "";
  }
}

function formatTime(value) {
  return formatReadableDateTime(value);
}

function compactDetail(value) {
  const text = String(value || "");
  if (!text) return "已写入审计链路";
  const translated = text
    .split(/[;,，]/)
    .map((item) => {
      const [level, action] = item.split(":");
      if (!action) return "已写入审计链路";
      return `${riskLabel(level)}风险，${actionLabel(action)}`;
    })
    .join("；");
  return translated.length <= 48 ? translated : `${translated.slice(0, 48)}...`;
}

watch(
  () => props.events[0]?.eventId,
  () => refreshAudit(),
);

watch(
  () => props.demoActionToken,
  (token, previousToken) => {
    if (!token || token === previousToken) return;
    submitAction("confirmed_fraud");
  },
);

onMounted(() => {
  refreshAudit();
  timer = window.setInterval(refreshAudit, 1800);
});

onBeforeUnmount(() => {
  if (timer !== null) window.clearInterval(timer);
});
</script>

<template>
  <section class="case-workbench">
    <div class="panel case-queue-panel">
      <div class="panel-head">
        <h2>待办列表</h2>
        <span>{{ queue.length }} 条待处理</span>
      </div>
      <div class="case-queue-list">
        <button
          v-for="event in queue"
          :key="`todo-${event.eventId}`"
          type="button"
          class="case-queue-row"
          :class="{ active: Number(focusEvent?.eventId) === Number(event.eventId) }"
          @click="emit('select-case', event)"
        >
          <strong>{{ formatReadableTime(event.timestamp) }}</strong>
          <span class="flow-path compact" aria-label="账户流向">
            <b class="latin-number">{{ event.srcNode }}</b>
            <i></i>
            <b class="latin-number">{{ event.dstNode }}</b>
          </span>
          <b class="case-queue-risk">{{ riskLabel(event.riskLevel) }} {{ formatScore(event.riskScore) }}</b>
        </button>
        <div v-if="queue.length === 0" class="case-empty">
          <strong>暂无待复核事件</strong>
          <span>高危告警进入后会出现在这里。</span>
        </div>
      </div>
    </div>

    <div class="panel case-current-panel">
      <div class="panel-head">
        <h2>当前案件</h2>
      </div>
      <div v-if="focusEvent" class="current-case-card">
        <div class="current-case-head">
          <div>
            <span>发生时间</span>
            <strong>{{ formatReadableTime(focusEvent.timestamp) }}</strong>
          </div>
          <b>{{ riskLabel(focusEvent.riskLevel) }} {{ formatScore(focusEvent.riskScore) }}</b>
        </div>
        <div class="current-case-grid">
          <span>
            账户链路
            <b class="flow-path compact" aria-label="账户流向">
              <em class="latin-number">{{ focusEvent.srcNode }}</em>
              <i></i>
              <em class="latin-number">{{ focusEvent.dstNode }}</em>
            </b>
          </span>
          <span>交易渠道 <b>{{ channelLabel(focusEvent.channel) }}</b></span>
          <span>交易金额 <b>{{ Number(focusEvent.amount || 0).toFixed(2) }} 元</b></span>
          <span>团伙编号 <b>{{ communityLabel(focusEvent.communityId || focusEvent.evidence?.graph_community_id) }}</b></span>
        </div>
        <div class="case-actions large">
          <button :disabled="Boolean(busyStatus)" @click="submitAction('confirmed_fraud')">{{ busyStatus === "confirmed_fraud" ? "写入中" : "确认欺诈" }}</button>
          <button :disabled="Boolean(busyStatus)" @click="submitAction('manual_block')">{{ busyStatus === "manual_block" ? "写入中" : "人工冻结" }}</button>
          <button :disabled="Boolean(busyStatus)" @click="submitAction('false_positive')">{{ busyStatus === "false_positive" ? "写入中" : "误报放行" }}</button>
        </div>
        <span v-if="writeError" class="case-write-error">{{ writeError }}</span>
      </div>
      <div v-else class="case-empty">
        <strong>请选择案件</strong>
        <span>左侧待办列表用于切换当前处置对象。</span>
      </div>
    </div>

    <div class="panel case-history-panel">
      <div class="panel-head">
        <h2>处置记录</h2>
        <span>{{ displayedCaseActions.length }} 条</span>
      </div>
      <div class="audit-list">
        <article v-for="action in displayedCaseActions.slice(0, actionLimit)" :key="`case-${action.case_id}-${action.updated_at}`" class="audit-item">
          <b>{{ statusText[action.status] || actionLabel(action.status) }}</b>
          <span class="latin-number">事件 {{ action.event_id }} / {{ formatTime(action.updated_at) }}</span>
        </article>
        <article v-if="displayedCaseActions.length === 0" class="audit-item muted-item">
          <b>暂无处置记录</b>
          <span>等待风险事件入库</span>
        </article>
      </div>
    </div>

    <div class="panel case-audit-trace-panel">
      <div class="panel-head">
        <h2>审计链路</h2>
        <span>{{ auditLogs.length }} 条</span>
      </div>
      <div class="audit-list">
        <article v-for="log in auditLogs.slice(0, auditLimit)" :key="`audit-${log.audit_id}-${log.created_at}`" class="audit-item">
          <b>{{ auditText[log.action] || "审计记录" }}</b>
          <span class="latin-number">事件 {{ log.event_id }} / {{ formatTime(log.created_at) }}</span>
          <span>{{ compactDetail(log.detail) }}</span>
        </article>
        <article v-if="auditLogs.length === 0" class="audit-item muted-item">
          <b>暂无审计日志</b>
          <span>等待评分服务写入</span>
        </article>
      </div>
    </div>
  </section>
</template>
