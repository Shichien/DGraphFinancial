<script setup>
import { computed } from "vue";
import {
  actionLabel,
  channelLabel,
  communityLabel,
  evidenceValueLabel,
  formatReadableTime,
  formatScore,
  fraudScriptLabel,
  levelColor,
  reasonLabel,
  riskLabel,
} from "../utils/format";

const props = defineProps({
  event: { type: Object, default: null },
  compact: { type: Boolean, default: false },
});

const evidence = computed(() => props.event?.evidence || {});
const detail = computed(() => props.event?.focusNodeDetail || {});
const scoreBreakdown = computed(() => detail.value?.scoreBreakdown || {});
const components = computed(() => scoreBreakdown.value?.components || []);
const relatedEdges = computed(() => props.event?.relatedEdges || []);
const reasonItems = computed(() => {
  const codes = props.event?.reasonCodes || [];
  return codes.length ? codes.map(reasonLabel) : ["模型评分命中"];
});
const pathItems = computed(() => {
  if (!props.event) return [];
  const base = [
    {
      label: "交易路径",
      source: props.event.srcNode ?? "--",
      target: props.event.dstNode ?? "--",
      note: channelLabel(props.event.channel),
    },
  ];
  const edgeItems = relatedEdges.value.slice(0, 5).map((edge) => ({
    label: "关联路径",
    source: edge.src_account ?? edge.source ?? "--",
    target: edge.dst_account ?? edge.target ?? "--",
    note: channelLabel(edge.relation_type || edge.channel || "related_node"),
  }));
  return [...base, ...edgeItems];
});

const basicRows = computed(() => {
  if (!props.event) return [];
  return [
    ["发生时间", formatReadableTime(props.event.timestamp)],
    ["源账户", props.event.srcNode],
    ["目标账户", props.event.dstNode],
    ["交易渠道", channelLabel(props.event.channel)],
    ["交易金额", `${Number(props.event.amount || 0).toFixed(2)} 元`],
    ["处置建议", actionLabel(props.event.action)],
  ];
});

const evidenceRows = computed(() => [
  ["命中剧本", fraudScriptLabel(evidence.value.fraud_script_type)],
  ["团伙编号", communityLabel(props.event?.communityId || evidence.value.graph_community_id)],
  ["共用设备账户", evidenceValueLabel("device_account_count", evidence.value.device_account_count)],
  ["同 IP 账户", evidenceValueLabel("ip_account_count", evidence.value.ip_account_count)],
  ["团伙邻居", evidenceValueLabel("graph_neighbor_count", evidence.value.graph_neighbor_count)],
  ["规则分", evidenceValueLabel("rule_score", evidence.value.rule_score)],
]);

function componentProgress(item) {
  const contribution = Number(item.contribution || 0);
  const weight = Number(item.weight || 0);
  if (!Number.isFinite(contribution) || !Number.isFinite(weight) || weight <= 0) return 0;
  return Math.max(0, Math.min(1, contribution / weight));
}
</script>

<template>
  <section class="panel case-detail-panel" :class="{ compact }">
    <div class="panel-head">
      <h2>案件详情</h2>
      <span>{{ event ? communityLabel(event.communityId || evidence.graph_community_id) : "等待选择案件" }}</span>
    </div>

    <div v-if="!event" class="case-empty">
      <strong>请选择一条告警</strong>
      <span>告警表格、团伙列表和图谱节点都会联动到这里。</span>
    </div>

    <template v-else>
      <div class="case-hero">
        <div>
          <span>发生时间</span>
          <strong>{{ formatReadableTime(event.timestamp) }}</strong>
        </div>
        <div class="case-score" :style="{ '--case-color': levelColor[event.riskLevel] || '#1f7a62' }">
          <span>{{ riskLabel(event.riskLevel) }}</span>
          <b class="latin-number">{{ formatScore(event.riskScore) }}</b>
        </div>
      </div>

      <div class="case-detail-grid">
        <div v-for="[label, value] in basicRows" :key="label" class="case-kv">
          <span>{{ label }}</span>
          <strong>{{ value }}</strong>
        </div>
      </div>

      <div class="case-section">
        <h3>交易链路</h3>
        <article v-for="item in pathItems" :key="`${item.label}-${item.source}-${item.target}`" class="path-row">
          <b>{{ item.label }}</b>
          <strong class="flow-path" aria-label="账户流向">
            <em class="latin-number">{{ item.source }}</em>
            <i></i>
            <em class="latin-number">{{ item.target }}</em>
          </strong>
          <span>{{ item.note }}</span>
        </article>
      </div>

      <div class="case-section">
        <h3>评分解释</h3>
        <div v-if="components.length" class="score-component-list">
          <div v-for="item in components.slice(0, compact ? 3 : 6)" :key="item.key" class="score-component">
            <span>{{ item.label }}</span>
            <div class="track" :style="{ '--progress': componentProgress(item) }"><i></i></div>
            <b class="latin-number">{{ formatScore(item.contribution) }}</b>
          </div>
        </div>
        <div v-else class="case-pill-row">
          <span v-for="reason in reasonItems" :key="reason" class="case-pill">{{ reason }}</span>
        </div>
      </div>

      <div class="case-section">
        <h3>团伙关系</h3>
        <div class="case-detail-grid small">
          <div v-for="[label, value] in evidenceRows" :key="label" class="case-kv">
            <span>{{ label }}</span>
            <strong>{{ value }}</strong>
          </div>
        </div>
      </div>

      <div v-if="!compact" class="case-section">
        <h3>原因码</h3>
        <div class="case-pill-row">
          <span v-for="reason in reasonItems" :key="reason" class="case-pill">{{ reason }}</span>
        </div>
      </div>
    </template>
  </section>
</template>
