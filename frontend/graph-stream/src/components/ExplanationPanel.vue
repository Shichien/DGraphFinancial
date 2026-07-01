<script setup>
import { computed } from "vue";
import { communityLabel, evidenceLabel, evidenceValueLabel, formatNumber, formatScore, levelColor, reasonSummary, riskLabel } from "../utils/format";

const props = defineProps({
  lastEvent: { type: Object, default: null },
});

const detail = computed(() => props.lastEvent?.focusNodeDetail ?? null);
const breakdown = computed(() => detail.value?.scoreBreakdown ?? null);
const level = computed(() => breakdown.value?.riskLevel || detail.value?.riskLevel || "low");
const metrics = computed(() => breakdown.value?.metrics ?? {});
const components = computed(() => breakdown.value?.components ?? []);
const evidence = computed(() => props.lastEvent?.evidence ?? {});
const reasonCodes = computed(() => props.lastEvent?.reasonCodes ?? []);
const relatedNodes = computed(() => props.lastEvent?.relatedNodes ?? []);

function contributionColor(value) {
  if (value >= 0.12) return levelColor.critical;
  if (value >= 0.07) return levelColor.high;
  if (value >= 0.035) return levelColor.medium;
  return levelColor.low;
}

function componentProgress(item) {
  const contribution = Number(item.contribution || 0);
  const weight = Number(item.weight || 0);
  if (!Number.isFinite(contribution) || !Number.isFinite(weight) || weight <= 0) {
    return 0;
  }
  return Math.max(0, Math.min(1, contribution / weight));
}

function evidenceValue(key, fallback = "--") {
  const value = evidence.value?.[key];
  if (value === undefined || value === null || value === "") return fallback;
  return value;
}

const evidenceItems = computed(() => [
  ["graph_community_id", props.lastEvent?.communityId || evidenceValue("graph_community_id", "")],
  ["device_account_count", evidenceValue("device_account_count", 0)],
  ["ip_account_count", evidenceValue("ip_account_count", 0)],
  ["burst_score", evidenceValue("burst_score", 0)],
]);

function componentTip(item) {
  const evidenceText = String(item.evidence || "").trim();
  if (/[\u4e00-\u9fa5]/.test(evidenceText)) return evidenceText;
  return `该项表示${item.label || "当前特征"}对风险分的影响`;
}
</script>

<template>
  <section class="explain-panel" aria-label="节点风险判定依据">
    <div class="explain-main">
      <div class="explain-kicker">当前焦点节点</div>
      <h2 id="explain-node" class="explain-title">
        {{ detail ? `节点 ${detail.id} 的风险判定` : "等待交易进入" }}
      </h2>
      <div class="explain-score-line">
        <strong id="explain-score" class="explain-score" :style="{ color: levelColor[level] || '#1f7a62' }">
          {{ breakdown ? formatScore(breakdown.finalScore) : "--" }}
        </strong>
        <span id="explain-level" class="explain-level" :style="{ '--level-color': levelColor[level] || '#1f7a62' }">
          {{ breakdown ? riskLabel(level) : "--" }}
        </span>
      </div>
      <div id="explain-formula" class="explain-formula">
        {{ breakdown ? (breakdown.formula || "综合风险分由静态模型先验和实时交易行为加权得到，条形表示该项特征强度，数字表示加权后的得分贡献。") : "系统将在交易进入后展示模型先验与动态行为贡献。" }}
      </div>
      <div id="explain-meta" class="explain-meta">
        <template v-if="breakdown">
          度 {{ formatNumber(metrics.degree) }} / 事件 {{ formatNumber(metrics.eventCount) }} / 时间跨度 {{ formatNumber(metrics.timeSpan) }} / 渠道 {{ formatNumber(metrics.channelCount) }} 类 / 交易类型 {{ formatNumber(metrics.edgeTypeCount) }} 类
        </template>
        <template v-else>--</template>
      </div>
      <div v-if="lastEvent" class="evidence-grid">
        <span v-for="[key, value] in evidenceItems" :key="key">
          {{ evidenceLabel(key) }} {{ evidenceValueLabel(key, value) }}
        </span>
      </div>
    </div>
    <div id="explain-bars" class="explain-bars">
      <div v-for="item in components" :key="item.key" class="explain-row" :title="componentTip(item)">
        <strong>{{ item.label }}</strong>
        <div class="track" :style="{ '--progress': componentProgress(item), '--bar-color': contributionColor(Number(item.contribution || 0)) }"><i></i></div>
        <em>{{ formatScore(item.contribution) }}</em>
      </div>
      <div class="reason-box">
        <strong>判定原因</strong>
        <span>{{ reasonCodes.length ? reasonSummary(reasonCodes, 4) : "等待原因码" }}</span>
      </div>
      <div class="reason-box">
        <strong>相关节点</strong>
        <span>{{ relatedNodes.length ? relatedNodes.slice(0, 6).join("、") : "等待图邻域证据" }}</span>
      </div>
    </div>
  </section>
</template>
