<script setup>
import { computed, ref, watch } from "vue";
import { actionLabel, channelLabel, communityLabel, formatReadableTime, formatScore, fraudScriptLabel, levelColor, riskLabel } from "../utils/format";

const props = defineProps({
  events: { type: Array, default: () => [] },
  selectedEventId: { type: [Number, String], default: null },
});

const emit = defineEmits(["select-alert"]);

const filters = ref({
  level: "all",
  channel: "all",
  script: "all",
  community: "all",
  action: "all",
});

const highRiskEvents = computed(() => props.events.filter((event) => ["critical", "high", "medium"].includes(event.riskLevel)));
const options = computed(() => ({
  levels: uniqueOptions(highRiskEvents.value.map((event) => event.riskLevel)),
  channels: uniqueOptions(highRiskEvents.value.map((event) => event.channel)),
  scripts: uniqueOptions(highRiskEvents.value.map((event) => event.evidence?.fraud_script_type).filter(Boolean)),
  communities: uniqueOptions(highRiskEvents.value.map((event) => event.communityId || event.evidence?.graph_community_id).filter(Boolean)),
  actions: uniqueOptions(highRiskEvents.value.map((event) => event.action)),
}));

const filteredEvents = computed(() =>
  highRiskEvents.value.filter((event) => {
    if (filters.value.level !== "all" && event.riskLevel !== filters.value.level) return false;
    if (filters.value.channel !== "all" && event.channel !== filters.value.channel) return false;
    if (filters.value.script !== "all" && event.evidence?.fraud_script_type !== filters.value.script) return false;
    const community = event.communityId || event.evidence?.graph_community_id;
    if (filters.value.community !== "all" && community !== filters.value.community) return false;
    if (filters.value.action !== "all" && event.action !== filters.value.action) return false;
    return true;
  }),
);

watch(
  () => props.events[0]?.eventId,
  () => {
    if (!props.selectedEventId && filteredEvents.value[0]) emit("select-alert", filteredEvents.value[0]);
  },
  { immediate: true },
);

function uniqueOptions(values) {
  return [...new Set(values.filter((value) => value !== undefined && value !== null && value !== ""))];
}
</script>

<template>
  <section class="panel alert-table-panel">
    <div class="panel-head">
      <h2>告警工作台</h2>
      <span>{{ filteredEvents.length }} 条结果</span>
    </div>

    <div class="table-filters">
      <label>
        <span>等级</span>
        <select v-model="filters.level">
          <option value="all">全部等级</option>
          <option v-for="level in options.levels" :key="level" :value="level">{{ riskLabel(level) }}</option>
        </select>
      </label>
      <label>
        <span>渠道</span>
        <select v-model="filters.channel">
          <option value="all">全部渠道</option>
          <option v-for="channel in options.channels" :key="channel" :value="channel">{{ channelLabel(channel) }}</option>
        </select>
      </label>
      <label>
        <span>剧本</span>
        <select v-model="filters.script">
          <option value="all">全部剧本</option>
          <option v-for="script in options.scripts" :key="script" :value="script">{{ fraudScriptLabel(script) }}</option>
        </select>
      </label>
      <label>
        <span>团伙</span>
        <select v-model="filters.community">
          <option value="all">全部团伙</option>
          <option v-for="community in options.communities" :key="community" :value="community">{{ communityLabel(community) }}</option>
        </select>
      </label>
      <label>
        <span>状态</span>
        <select v-model="filters.action">
          <option value="all">全部状态</option>
          <option v-for="action in options.actions" :key="action" :value="action">{{ actionLabel(action) }}</option>
        </select>
      </label>
    </div>

    <div class="alert-table-wrap">
      <table class="alert-table">
        <thead>
          <tr>
            <th>时间</th>
            <th>等级</th>
            <th>风险分</th>
            <th>账户链路</th>
            <th>渠道</th>
            <th>剧本</th>
            <th>团伙</th>
            <th>状态</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="event in filteredEvents"
            :key="`row-${event.eventId}-${event.riskScore}`"
            :class="{ active: Number(selectedEventId) === Number(event.eventId) }"
            @click="emit('select-alert', event)"
          >
            <td>{{ formatReadableTime(event.timestamp) }}</td>
            <td><b :style="{ color: levelColor[event.riskLevel] || '#1f7a62' }">{{ riskLabel(event.riskLevel) }}</b></td>
            <td class="latin-number">{{ formatScore(event.riskScore) }}</td>
            <td>
              <span class="flow-path compact" aria-label="账户流向">
                <b class="latin-number">{{ event.srcNode }}</b>
                <i></i>
                <b class="latin-number">{{ event.dstNode }}</b>
              </span>
            </td>
            <td>{{ channelLabel(event.channel) }}</td>
            <td>{{ fraudScriptLabel(event.evidence?.fraud_script_type) }}</td>
            <td>{{ communityLabel(event.communityId || event.evidence?.graph_community_id) }}</td>
            <td>{{ actionLabel(event.action) }}</td>
          </tr>
          <tr v-if="filteredEvents.length === 0">
            <td colspan="8" class="table-empty">当前筛选下没有告警</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
