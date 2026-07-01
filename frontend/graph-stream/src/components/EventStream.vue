<script setup>
import { computed } from "vue";
import { actionLabel, channelLabel, communityLabel, formatReadableTime, formatScore, levelColor, riskLabel } from "../utils/format";

const props = defineProps({
  events: { type: Array, default: () => [] },
  limit: { type: Number, default: 6 },
});

const rows = computed(() => props.events.slice(0, props.limit));

</script>

<template>
  <section class="panel">
    <div class="panel-head"><h2>实时交易监测</h2></div>
    <div id="event-stream" class="event-stream">
      <article v-for="event in rows" :key="`${event.eventId}-${event.riskLevel}-${formatScore(event.riskScore)}`" class="event-item">
        <span>{{ channelLabel(event.channel) }} / {{ formatReadableTime(event.timestamp) }}</span>
        <strong>
          <b class="flow-path event-flow" aria-label="账户流向">
            <em class="latin-number">{{ event.srcNode }}</em>
            <i></i>
            <em class="latin-number">{{ event.dstNode }}</em>
          </b>
          <b class="serif-strong" :style="{ color: levelColor[event.riskLevel] || '#1f7a62' }">{{ riskLabel(event.riskLevel) }}</b>
        </strong>
        <div class="event-meta-grid">
          <span>风险分 {{ formatScore(event.riskScore) }}</span>
          <span>处理动作 {{ actionLabel(event.action) }}</span>
          <span>{{ communityLabel(event.communityId) }}</span>
          <span>交易金额 {{ Number(event.amount || 0).toFixed(2) }} 元</span>
        </div>
      </article>
    </div>
  </section>
</template>
