<script setup>
import { formatScore, levelColor, riskLabel, truthLabel } from "../utils/format";

defineProps({
  nodes: { type: Array, default: () => [] },
  limit: { type: Number, default: 4 },
});
</script>

<template>
  <section class="panel node-ranking-panel">
    <div class="panel-head"><h2>团伙关系证据</h2></div>
    <div id="node-list" class="node-list">
      <article v-for="node in nodes.slice(0, limit)" :key="`${node.id}-${node.riskLevel}-${formatScore(node.riskScore)}-${node.degree}-${node.eventCount}`" class="node-row">
        <span>{{ node.detectedFraud ? "团伙核心节点" : "关联观察节点" }} / {{ truthLabel(node.groundTruth) }}</span>
        <strong>
          <b class="latin-number">{{ node.id }}</b>
          <b :style="{ color: levelColor[node.riskLevel] || '#45b591' }">
            <span class="serif-strong">{{ riskLabel(node.riskLevel) }}</span>
            <span class="latin-number">{{ formatScore(node.riskScore) }}</span>
          </b>
        </strong>
        <span>邻接度 {{ node.degree }} / 相关交易 {{ node.eventCount }} / 模型先验 {{ formatScore(node.staticScore) }}</span>
      </article>
    </div>
  </section>
</template>
