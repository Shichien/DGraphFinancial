<script setup>
import { computed } from "vue";
import { actionLabel, channelLabel, communityLabel, formatReadableTime, formatScore, levelColor, reasonSummary, riskLabel } from "../utils/format";

const props = defineProps({
  events: { type: Array, default: () => [] },
  summary: { type: Object, default: () => ({}) },
  limit: { type: Number, default: 5 },
});

const emit = defineEmits(["select-alert"]);

const alerts = computed(() => props.events.filter((event) => ["critical", "high"].includes(event.riskLevel)).slice(0, props.limit));

</script>

<template>
  <section class="panel alert-panel">
    <div class="panel-head">
      <h2>告警队列</h2>
      <span>高危 {{ summary.alertCount || alerts.length }}</span>
    </div>
    <div class="alert-list">
      <article
        v-for="event in alerts"
        :key="`alert-${event.eventId}-${event.riskScore}`"
        class="alert-card clickable"
        role="button"
        tabindex="0"
        @click="emit('select-alert', event)"
        @keydown.enter.prevent="emit('select-alert', event)"
        @keydown.space.prevent="emit('select-alert', event)"
      >
        <div class="alert-top">
          <strong>{{ formatReadableTime(event.timestamp) }}</strong>
          <b :style="{ color: levelColor[event.riskLevel] || '#bc7a1b' }">{{ riskLabel(event.riskLevel) }}</b>
        </div>
        <div class="alert-score-line">
          <span>风险分</span>
          <strong class="latin-number">{{ formatScore(event.riskScore) }}</strong>
          <em>{{ actionLabel(event.action) }}</em>
        </div>
        <div class="alert-meta">
          <span>{{ channelLabel(event.channel) }}</span>
          <span>{{ communityLabel(event.communityId) }}</span>
          <span>交易金额 {{ Number(event.amount || 0).toFixed(2) }} 元</span>
        </div>
        <p>{{ reasonSummary(event.reasonCodes) }}</p>
      </article>
      <article v-if="alerts.length === 0" class="alert-card muted-item">
        <div class="alert-top">
          <strong>暂无高危告警</strong>
        </div>
        <p>实时评分达到高危或严重等级后，会自动进入告警队列。</p>
      </article>
    </div>
  </section>
</template>
