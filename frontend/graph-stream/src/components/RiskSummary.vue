<script setup>
import { computed } from "vue";
import { formatNumber, levelColor } from "../utils/format";

const props = defineProps({
  summary: { type: Object, default: () => ({}) },
});

const levels = computed(() => [
  ["critical", props.summary.criticalCount || 0, "严重风险"],
  ["high", props.summary.highCount || 0, "高危风险"],
  ["medium", props.summary.mediumCount || 0, "中危风险"],
  ["low", props.summary.lowCount || 0, "低危风险"],
]);

</script>

<template>
  <section class="panel">
    <div class="panel-head"><h2>风险统计</h2></div>
    <div class="risk-summary">
      <div class="risk-summary-grid">
        <div v-for="[level, count, label] in levels" :key="level" class="risk-chip">
          <span>{{ label }}</span>
          <strong :id="`risk-${level}`" :style="{ color: levelColor[level] }">{{ formatNumber(count) }}</strong>
        </div>
      </div>
    </div>
  </section>
</template>
