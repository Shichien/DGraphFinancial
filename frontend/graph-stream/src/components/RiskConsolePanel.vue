<script setup>
import { computed, onMounted, ref } from "vue";
import { fetchRiskConsoleSchema, runRiskConsole } from "../api/graphStream";
import { actionLabel, formatScore, fraudScriptLabel, levelColor, riskLabel } from "../utils/format";

const examples = [
  {
    id: "single-low",
    label: "低风险单笔",
    payload: {
      reset_before: true,
      history_limit: 120,
      commands: [
        {
          type: "send",
          src: 120,
          dst: 220,
          amount: 800,
          channel: "wallet_pay",
          historical_risk: 0.08,
          fraud_type: "none",
          scripted: false,
        },
      ],
    },
  },
  {
    id: "device-batch",
    label: "设备复用批次",
    payload: {
      reset_before: true,
      history_limit: 120,
      commands: [
        {
          type: "set",
          defaults: {
            channel: "wallet_pay",
            historical_risk: 0.72,
            fraud_type: "device_reuse",
            scripted: true,
          },
        },
        {
          type: "batch",
          count: 18,
          src: { range: [500, 517] },
          dst: 650,
          amount: { range: [2000, 96000] },
          shared_device: true,
          shared_ip: true,
          blacklist: "device",
          login: { cycle: ["success", "challenge"] },
        },
      ],
    },
  },
  {
    id: "merchant-batch",
    label: "商户洗钱批次",
    payload: {
      reset_before: true,
      history_limit: 120,
      commands: [
        {
          type: "batch",
          count: 14,
          src: { range: [700, 713] },
          dst: { range: [810, 823] },
          amount: { cycle: [6800, 22000, 87000, 125000] },
          merchant: "m_launder_010",
          device: { cycle: ["d_web_1", "d_web_2", "d_web_3"] },
          ip: { cycle: ["10.20.1.7", "10.20.1.8"] },
          blacklist: "merchant",
          fraud_type: "merchant_laundering",
          scripted: true,
          historical_risk: { range: [0.35, 0.92] },
        },
      ],
    },
  },
  {
    id: "mixed-flow",
    label: "跨渠道混合",
    payload: {
      reset_before: true,
      history_limit: 160,
      commands: [
        {
          type: "batch",
          count: 8,
          src: { range: [900, 907] },
          dst: { range: [1000, 1007] },
          amount: { range: [300, 4800] },
          channel: { cycle: ["wallet_pay", "mobile_banking"] },
          historical_risk: { range: [0.05, 0.22] },
        },
        {
          type: "batch",
          count: 12,
          src: { range: [910, 921] },
          dst: 1088,
          amount: { range: [12000, 140000] },
          channel: { cycle: ["wallet_pay", "bank_transfer", "merchant_acquire"] },
          shared_device: true,
          shared_merchant: true,
          blacklist: "account",
          fraud_type: "cross_channel_evasion",
          scripted: true,
          historical_risk: { range: [0.48, 0.96] },
        },
      ],
    },
  },
];

const valueModes = [
  { value: "string", label: "文本" },
  { value: "number", label: "数字" },
  { value: "boolean", label: "布尔" },
  { value: "range", label: "范围" },
  { value: "cycle", label: "循环" },
  { value: "json", label: "JSON" },
];

let nextBuilderId = 5;
const commandText = ref(JSON.stringify(examples[1].payload, null, 2));
const builderType = ref("batch");
const builderCount = ref(12);
const builderRows = ref([
  { id: 1, field: "src", mode: "range", value: "500..511" },
  { id: 2, field: "amount", mode: "range", value: "1200..98000" },
  { id: 3, field: "shared_device", mode: "boolean", value: "true" },
  { id: 4, field: "blacklist", mode: "string", value: "device" },
]);
const schema = ref(null);
const response = ref(null);
const selectedIndex = ref(0);
const running = ref(false);
const error = ref("");

const resultRows = computed(() => response.value?.results || []);
const historyRows = computed(() => response.value?.history || []);
const summary = computed(() => response.value?.summary || { event_count: 0, risk_level_counts: {}, reason_counts: {}, top_events: [] });
const historySummary = computed(() => response.value?.historySummary || { event_count: 0, risk_level_counts: {}, reason_counts: {}, top_events: [] });
const state = computed(() => response.value?.state || schema.value?.state || {});
const selectedResult = computed(() => resultRows.value[selectedIndex.value] || resultRows.value[0] || null);
const selectedDecision = computed(() => selectedResult.value?.decision || {});
const selectedInput = computed(() => selectedResult.value?.input?.transaction || {});
const selectedFeatures = computed(() => selectedResult.value?.features || {});
const selectedSummary = computed(() => selectedResult.value?.summary || {});
const aliasRows = computed(() => Object.entries(schema.value?.aliases || {}).slice(0, 18));
const reasonRows = computed(() => Object.entries(summary.value.reason_counts || {}).slice(0, 10));
const topRows = computed(() => summary.value.top_events || []);
const scoreRows = computed(() => selectedResult.value?.score_breakdown || []);
const maxContribution = computed(() => Math.max(0.001, ...scoreRows.value.map((row) => Math.abs(Number(row.contribution || 0)))));
const featureRows = computed(() =>
  Object.entries(selectedFeatures.value)
    .filter(([, value]) => value !== null && value !== undefined)
    .slice(0, 18),
);
const levelCounts = computed(() => {
  const counts = summary.value.risk_level_counts || {};
  return [
    ["critical", counts.critical || 0],
    ["high", counts.high || 0],
    ["medium", counts.medium || 0],
    ["low", counts.low || 0],
  ];
});

function selectExample(example) {
  commandText.value = JSON.stringify(example.payload, null, 2);
  error.value = "";
}

function parseEditor() {
  const parsed = JSON.parse(commandText.value);
  if (Array.isArray(parsed)) {
    return { commands: parsed, history_limit: 120 };
  }
  if (parsed && typeof parsed === "object") {
    if (parsed.commands || parsed.command || parsed.reset_before !== undefined || parsed.history_limit !== undefined) {
      return { history_limit: 120, ...parsed };
    }
    return { commands: [parsed], history_limit: 120 };
  }
  throw new Error("请输入合法 JSON");
}

function formatEditor() {
  try {
    commandText.value = JSON.stringify(parseEditor(), null, 2);
    error.value = "";
  } catch (exc) {
    error.value = exc.message;
  }
}

async function execute() {
  running.value = true;
  error.value = "";
  try {
    const payload = parseEditor();
    response.value = await runRiskConsole(payload);
    selectedIndex.value = 0;
  } catch (exc) {
    error.value = exc.message;
  } finally {
    running.value = false;
  }
}

async function resetSession() {
  running.value = true;
  error.value = "";
  try {
    response.value = await runRiskConsole({ commands: [{ type: "reset" }], history_limit: 120 });
    selectedIndex.value = 0;
    await loadSchema();
  } catch (exc) {
    error.value = exc.message;
  } finally {
    running.value = false;
  }
}

function addBuilderRow() {
  builderRows.value.push({ id: nextBuilderId, field: "transaction.amount", mode: "number", value: "1000" });
  nextBuilderId += 1;
}

function removeBuilderRow(id) {
  builderRows.value = builderRows.value.filter((row) => row.id !== id);
}

function buildCommandFromRows() {
  try {
    const command = { type: builderType.value };
    if (builderType.value === "batch") {
      command.count = Number(builderCount.value || 1);
    }
    for (const row of builderRows.value) {
      const field = String(row.field || "").trim();
      if (!field) throw new Error("字段不能为空");
      command[field] = parseBuilderValue(row);
    }
    commandText.value = JSON.stringify({ history_limit: 120, commands: [command] }, null, 2);
    error.value = "";
  } catch (exc) {
    error.value = exc.message;
  }
}

function parseBuilderValue(row) {
  const raw = String(row.value ?? "").trim();
  if (row.mode === "number") return Number(raw);
  if (row.mode === "boolean") return ["true", "1", "yes", "on"].includes(raw.toLowerCase());
  if (row.mode === "range") {
    const [start, end] = raw.split("..");
    if (start === undefined || end === undefined) throw new Error("范围格式为 start..end");
    return { range: [parseLooseScalar(start), parseLooseScalar(end)] };
  }
  if (row.mode === "cycle") {
    return { cycle: raw.split(",").map((item) => parseLooseScalar(item.trim())) };
  }
  if (row.mode === "json") return JSON.parse(raw);
  return raw;
}

function parseLooseScalar(value) {
  if (value === "") return "";
  if (value.toLowerCase() === "true") return true;
  if (value.toLowerCase() === "false") return false;
  const numeric = Number(value);
  return Number.isFinite(numeric) && value.trim() !== "" ? numeric : value;
}

function displayValue(value) {
  if (Array.isArray(value)) return value.join(", ");
  if (value && typeof value === "object") return JSON.stringify(value);
  if (typeof value === "boolean") return value ? "true" : "false";
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : value.toFixed(4);
  return value === null || value === undefined || value === "" ? "--" : String(value);
}

function contributionWidth(row) {
  return `${Math.min(100, Math.abs(Number(row.contribution || 0)) / maxContribution.value * 100)}%`;
}

async function loadSchema() {
  try {
    schema.value = await fetchRiskConsoleSchema();
  } catch (exc) {
    error.value = exc.message;
  }
}

onMounted(loadSchema);
</script>

<template>
  <div class="risk-console-page">
    <div class="risk-console-left-column">
      <section class="panel risk-console-editor">
        <div class="panel-head">
          <h2>交易生成控制台</h2>
          <span>{{ state.result_count || 0 }} 条历史结果</span>
        </div>

        <div class="console-template-row" aria-label="控制台模板">
          <button v-for="example in examples" :key="example.id" type="button" @click="selectExample(example)">
            {{ example.label }}
          </button>
        </div>

        <div class="console-builder">
          <div class="console-builder-head">
            <label>
              <span>命令类型</span>
              <select v-model="builderType">
                <option value="send">send</option>
                <option value="batch">batch</option>
                <option value="set">set</option>
              </select>
            </label>
            <label>
              <span>批量条数</span>
              <input v-model.number="builderCount" min="1" max="500" type="number" />
            </label>
            <button type="button" @click="addBuilderRow">添加字段</button>
            <button type="button" @click="buildCommandFromRows">生成命令</button>
          </div>

          <div class="console-builder-rows">
            <div v-for="row in builderRows" :key="row.id" class="console-builder-row">
              <input v-model="row.field" aria-label="字段路径" />
              <select v-model="row.mode" aria-label="取值模式">
                <option v-for="mode in valueModes" :key="mode.value" :value="mode.value">{{ mode.label }}</option>
              </select>
              <input v-model="row.value" aria-label="字段取值" />
              <button type="button" aria-label="移除字段" @click="removeBuilderRow(row.id)">-</button>
            </div>
          </div>
        </div>

        <label class="console-json-editor">
          <span>命令 JSON</span>
          <textarea v-model="commandText" spellcheck="false"></textarea>
        </label>

        <div class="console-actions">
          <button type="button" :disabled="running" @click="execute">{{ running ? "执行中" : "运行" }}</button>
          <button type="button" :disabled="running" @click="formatEditor">格式化</button>
          <button type="button" :disabled="running" @click="resetSession">重置会话</button>
        </div>
        <p v-if="error" class="console-error">{{ error }}</p>

        <div class="console-alias-list">
          <span v-for="[alias, path] in aliasRows" :key="alias">
            <b>{{ alias }}</b>
            {{ path }}
          </span>
        </div>
      </section>

      <section class="panel risk-console-history">
        <div class="panel-head">
          <h2>会话历史</h2>
          <span>{{ historyRows.length }} 条最近结果</span>
        </div>
        <div class="console-history-list">
          <article v-for="result in historyRows.slice().reverse()" :key="`${result.summary.event_id}-${result.summary.risk_score}`">
            <strong>{{ result.summary.event_id }} / {{ result.summary.src_account }} -> {{ result.summary.dst_account }}</strong>
            <span>{{ riskLabel(result.decision.risk_level) }} {{ formatScore(result.decision.risk_score) }} / {{ actionLabel(result.decision.decision) }}</span>
          </article>
          <div v-if="historyRows.length === 0" class="case-empty">
            <strong>暂无会话历史</strong>
            <span>运行结果会保留在当前后端会话</span>
          </div>
        </div>
      </section>
    </div>

    <div class="risk-console-right-column">
      <section class="panel risk-console-output">
      <div class="panel-head">
        <h2>模型输出</h2>
        <span>本次 {{ summary.event_count || 0 }} 条 / 累计 {{ historySummary.event_count || 0 }} 条</span>
      </div>

      <div class="console-summary-grid">
        <article v-for="[level, count] in levelCounts" :key="level" :style="{ '--level-color': levelColor[level] || '#1f7a62' }">
          <span>{{ riskLabel(level) }}</span>
          <strong>{{ count }}</strong>
        </article>
      </div>

      <div class="console-output-grid">
        <div class="console-result-table-wrap">
          <table class="console-result-table">
            <thead>
              <tr>
                <th>Event</th>
                <th>账户</th>
                <th>金额</th>
                <th>等级</th>
                <th>分数</th>
                <th>处置</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(result, index) in resultRows"
                :key="result.summary.event_id"
                :class="{ active: index === selectedIndex }"
                @click="selectedIndex = index"
              >
                <td>{{ result.summary.event_id }}</td>
                <td>{{ result.summary.src_account }} -> {{ result.summary.dst_account }}</td>
                <td>{{ displayValue(result.input.transaction.amount) }}</td>
                <td>
                  <b :style="{ color: levelColor[result.decision.risk_level] || '#1f7a62' }">{{ riskLabel(result.decision.risk_level) }}</b>
                </td>
                <td>{{ formatScore(result.decision.risk_score) }}</td>
                <td>{{ actionLabel(result.decision.decision) }}</td>
              </tr>
              <tr v-if="resultRows.length === 0">
                <td class="table-empty" colspan="6">暂无本次结果</td>
              </tr>
            </tbody>
          </table>
        </div>

        <aside class="console-side">
          <div class="console-reason-list">
            <strong>原因码统计</strong>
            <span v-for="[reason, count] in reasonRows" :key="reason">
              <b>{{ reason }}</b>
              {{ count }}
            </span>
            <span v-if="reasonRows.length === 0">暂无原因码</span>
          </div>

          <div class="console-top-list">
            <strong>Top 结果</strong>
            <button v-for="item in topRows" :key="item.event_id" type="button" @click="selectedIndex = resultRows.findIndex((row) => row.summary.event_id === item.event_id)">
              <span>{{ item.event_id }} / {{ item.src_account }} -> {{ item.dst_account }}</span>
              <b>{{ formatScore(item.risk_score) }}</b>
            </button>
            <span v-if="topRows.length === 0">暂无排序结果</span>
          </div>
        </aside>
      </div>
      </section>

      <section class="panel risk-console-detail">
      <div class="panel-head">
        <h2>单条解释</h2>
        <span v-if="selectedResult">Event {{ selectedSummary.event_id }}</span>
        <span v-else>等待选择</span>
      </div>

      <template v-if="selectedResult">
        <div class="console-decision-card" :style="{ '--level-color': levelColor[selectedDecision.risk_level] || '#1f7a62' }">
          <div>
            <span>风险等级</span>
            <strong>{{ riskLabel(selectedDecision.risk_level) }}</strong>
          </div>
          <div>
            <span>模型分数</span>
            <strong>{{ formatScore(selectedDecision.risk_score) }}</strong>
          </div>
          <div>
            <span>处置建议</span>
            <strong>{{ actionLabel(selectedDecision.decision) }}</strong>
          </div>
          <div>
            <span>剧本类型</span>
            <strong>{{ fraudScriptLabel(selectedFeatures.fraud_script_type) }}</strong>
          </div>
        </div>

        <div class="console-kv-grid">
          <span>
            <b>源账户</b>
            {{ selectedInput.src_account }}
          </span>
          <span>
            <b>目标账户</b>
            {{ selectedInput.dst_account }}
          </span>
          <span>
            <b>设备</b>
            {{ selectedInput.device_id }}
          </span>
          <span>
            <b>IP</b>
            {{ selectedInput.ip }}
          </span>
          <span>
            <b>商户</b>
            {{ selectedInput.merchant_id }}
          </span>
          <span>
            <b>团伙</b>
            {{ selectedDecision.community_id || "--" }}
          </span>
        </div>

        <div class="console-breakdown-list">
          <div v-for="row in scoreRows" :key="row.name" class="console-breakdown-row">
            <span>{{ row.name }}</span>
            <i><em :style="{ width: contributionWidth(row) }"></em></i>
            <b>{{ displayValue(row.contribution) }}</b>
          </div>
        </div>

        <div class="console-feature-list">
          <span v-for="[key, value] in featureRows" :key="key">
            <b>{{ key }}</b>
            {{ displayValue(value) }}
          </span>
        </div>
      </template>

      <div v-else class="case-empty">
        <strong>暂无模型解释</strong>
        <span>运行一次命令后显示输出</span>
      </div>
      </section>
    </div>
  </div>
</template>
