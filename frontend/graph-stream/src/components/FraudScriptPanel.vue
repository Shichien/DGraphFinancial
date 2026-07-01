<script setup>
import { computed } from "vue";
import { formatNumber, formatScore, fraudScriptLabel } from "../utils/format";

const props = defineProps({
  scripts: { type: Array, default: () => [] },
  limit: { type: Number, default: 4 },
});

const rows = computed(() => props.scripts.slice(0, props.limit));
const maxCount = computed(() => Math.max(1, ...rows.value.map((item) => Number(item.count || 0))));
</script>

<template>
  <section class="panel script-panel">
    <div class="panel-head"><h2>欺诈剧本</h2></div>
    <div class="script-list">
      <article v-for="item in rows" :key="item.type" class="script-row">
        <div>
          <b>{{ fraudScriptLabel(item.type) }}</b>
          <span>最高风险 {{ formatScore(item.maxRiskScore) }} / 平均 {{ formatScore(item.avgRiskScore) }}</span>
        </div>
        <strong class="latin-number">{{ formatNumber(item.count) }}</strong>
        <div class="track" :style="{ '--progress': Number(item.count || 0) / maxCount }"><i></i></div>
      </article>
      <article v-if="rows.length === 0" class="script-row muted-item">
        <div>
          <b>等待剧本命中</b>
          <span>评分证据入库后自动汇总</span>
        </div>
        <strong class="latin-number">0</strong>
        <div class="track" style="--progress: 0"><i></i></div>
      </article>
    </div>
  </section>
</template>
