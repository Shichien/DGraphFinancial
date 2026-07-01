<script setup>
import { computed, watch } from "vue";
import { formatNumber, formatScore } from "../utils/format";
import { flashMetric } from "../composables/useMetricFlash";

const props = defineProps({
  summary: { type: Object, default: () => ({}) },
  streamMetrics: { type: Object, default: () => ({}) },
});

const metrics = computed(() => [
  { id: "m-events", label: "窗口交易", value: props.summary.windowEventCount, unit: "", numeric: "integer" },
  { id: "m-fraud", label: "疑似欺诈节点", value: props.summary.detectedFraudNodeCount, unit: "", numeric: "integer" },
  { id: "m-critical", label: "严重风险", value: props.summary.criticalCount, unit: "", numeric: "integer" },
  { id: "m-high", label: "高危风险", value: props.summary.highCount, unit: "", numeric: "integer" },
  { id: "m-medium", label: "中危风险", value: props.summary.mediumCount, unit: "", numeric: "integer" },
]);

function metricValue(item) {
  const value = item.numeric === "decimal" ? formatScore(item.value) : formatNumber(item.value);
  return item.unit ? `${value} ${item.unit}` : value;
}

watch(
  () => metrics.value.map((item) => item.value).join("|"),
  (_, oldValue) => {
    if (oldValue === undefined) return;
    metrics.value.forEach((item) => flashMetric(item.id));
  },
);
</script>

<template>
  <div class="metrics">
    <article v-for="item in metrics" :key="item.id" class="metric">
      <span>{{ item.label }}</span>
      <strong :id="item.id">{{ metricValue(item) }}</strong>
    </article>
  </div>
</template>
