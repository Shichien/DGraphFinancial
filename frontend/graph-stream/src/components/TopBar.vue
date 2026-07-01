<script setup>
import { computed } from "vue";
import { formatScore } from "../utils/format";

const props = defineProps({
  meta: { type: Object, default: () => ({}) },
  streamMetrics: { type: Object, default: () => ({}) },
  connected: { type: Boolean, default: true },
  theme: { type: String, default: "light" },
  replaying: { type: Boolean, default: false },
  demoRunning: { type: Boolean, default: false },
});

defineEmits(["toggle-theme", "replay", "toggle-demo"]);

const throughput = computed(() => `${formatScore(props.streamMetrics.kafkaThroughput ?? props.meta.eventsPerSecond)} 笔/秒`);
const flinkLatency = computed(() => `${formatScore(props.streamMetrics.flinkLatencyMs ?? 0)} ms`);
</script>

<template>
  <header class="topbar">
    <div class="brand">
      <div class="brand-mark">DG</div>
      <div>
        <strong>DGraph-Fin 动态交易图</strong>
      </div>
      <button class="demo-button top-demo-button" type="button" @click="$emit('toggle-demo')">{{ demoRunning ? "停止" : "演示" }}</button>
    </div>
    <div class="top-actions">
      <div class="top-meta">
        <span id="throughput" class="desktop-status">Kafka {{ throughput }}</span>
        <span id="flink-latency" class="desktop-status">Flink {{ flinkLatency }}</span>
      </div>
      <nav class="product-actions" aria-label="产品操作">
        <button class="product-button" type="button" :disabled="replaying" @click="$emit('replay')">重新回放</button>
        <button class="product-button theme-toggle" type="button" :aria-label="theme === 'dark' ? '切换浅色模式' : '切换深色模式'" :title="theme === 'dark' ? '切换浅色模式' : '切换深色模式'" @click="$emit('toggle-theme')">
          <span class="theme-icon" aria-hidden="true">
            <i class="theme-sun"></i>
            <i class="theme-moon"></i>
          </span>
        </button>
      </nav>
    </div>
  </header>
</template>
