<script setup>
import { computed, ref } from "vue";
import { channelLabel, communityLabel, formatReadableTime, formatScore, riskLabel } from "../utils/format";

const props = defineProps({
  events: { type: Array, default: () => [] },
});

const emit = defineEmits(["select-result"]);
const query = ref("");

const results = computed(() => {
  const keyword = query.value.trim().toLowerCase();
  if (!keyword) return [];
  return props.events
    .filter((event) => {
      const evidence = event.evidence || {};
      const values = [
        event.eventId,
        event.srcNode,
        event.dstNode,
        event.focusNode,
        event.channel,
        event.communityId,
        evidence.graph_community_id,
        evidence.device_id,
        evidence.ip,
        evidence.merchant_id,
        evidence.fraud_script_type,
      ];
      return values.some((value) => String(value ?? "").toLowerCase().includes(keyword));
    })
    .slice(0, 6);
});

function choose(event) {
  emit("select-result", event);
  query.value = "";
}
</script>

<template>
  <div class="global-search">
    <input v-model="query" type="search" placeholder="搜索事件、账户、设备、IP、商户、团伙" aria-label="全局搜索" />
    <div v-if="results.length" class="global-search-results">
      <button v-for="event in results" :key="`search-${event.eventId}`" type="button" @click="choose(event)">
        <strong>{{ formatReadableTime(event.timestamp) }}</strong>
        <span>{{ riskLabel(event.riskLevel) }} / {{ formatScore(event.riskScore) }}</span>
        <span>
          <b class="flow-path compact" aria-label="账户流向">
            <em class="latin-number">{{ event.srcNode }}</em>
            <i></i>
            <em class="latin-number">{{ event.dstNode }}</em>
          </b>
          / {{ channelLabel(event.channel) }}
        </span>
        <span>{{ communityLabel(event.communityId || event.evidence?.graph_community_id) }}</span>
      </button>
    </div>
  </div>
</template>
