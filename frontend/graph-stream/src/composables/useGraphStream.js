import { computed, onBeforeUnmount, ref } from "vue";
import { fetchDataSources, fetchGraphStream, resetGraphStream, switchDataSource as switchDataSourceApi } from "../api/graphStream";

const DEFAULT_DATA_SOURCES = [
  {
    key: "kafka_live",
    label: "Kafka 实时链路",
    description: "读取 Kafka、Flink、评分服务写入的风险事件库，展示真实实时链路结果。",
    mode: "Kafka 实时链路",
  },
  {
    key: "simulator",
    label: "多源仿真流",
    description: "持续生成银行转账、钱包支付、商户收单、设备登录和黑名单事件。",
    mode: "多源仿真流实时评分",
  },
  {
    key: "dgraph_replay",
    label: "DGraph 风险先验回放",
    description: "使用 DGraph-Fin 风险账户先验驱动实时交易回放，突出图结构风险传播。",
    mode: "DGraph 风险先验回放",
  },
  {
    key: "amlsim_sample",
    label: "AMLSim 样例回放",
    description: "从本地 AMLSim 样例交易文件回放账户转账和洗钱模式。",
    mode: "AMLSim 样例回放",
  },
  {
    key: "ieee_cis",
    label: "IEEE 交易回放",
    description: "从 IEEE-CIS 交易表抽取金额、卡号和欺诈标签，转换为实时交易事件。",
    mode: "IEEE 交易回放",
  },
];

export function useGraphStream(intervalMs = 650) {
  const snapshot = ref(null);
  const connected = ref(true);
  const replaying = ref(false);
  const paused = ref(false);
  const speed = ref(1);
  const replayToken = ref(0);
  const dataSources = ref(DEFAULT_DATA_SOURCES);
  const activeDataSource = ref("simulator");
  const switchingDataSource = ref(false);
  const dataSourceError = ref("");
  const graphView = ref("window");
  let timer = null;

  async function refresh({ force = false } = {}) {
    if (paused.value && !force) return;
    try {
      snapshot.value = await fetchGraphStream({ batchSize: Math.max(1, Math.round(120 * speed.value)), view: graphView.value });
      connected.value = true;
    } catch {
      connected.value = false;
    }
  }

  function stopTimer() {
    if (timer !== null) {
      window.clearInterval(timer);
      timer = null;
    }
  }

  function start(initialView = graphView.value) {
    stopTimer();
    graphView.value = initialView === "cumulative" ? "cumulative" : "window";
    loadDataSources();
    refresh();
    timer = window.setInterval(refresh, Math.max(180, Math.round(intervalMs / speed.value)));
  }

  function setPaused(nextPaused) {
    paused.value = nextPaused;
    if (!nextPaused) refresh();
  }

  function setSpeed(nextSpeed) {
    speed.value = Number(nextSpeed) || 1;
    if (timer !== null) start();
  }

  async function setGraphView(nextView) {
    const normalized = nextView === "cumulative" ? "cumulative" : "window";
    if (normalized === graphView.value) return;
    graphView.value = normalized;
    await refresh({ force: true });
  }

  async function replay() {
    replaying.value = true;
    try {
      await resetGraphStream();
      snapshot.value = null;
      replayToken.value += 1;
      await refresh({ force: true });
      window.setTimeout(() => {
        replayToken.value += 1;
      }, 40);
    } finally {
      replaying.value = false;
    }
  }

  async function loadDataSources() {
    try {
      const payload = await fetchDataSources();
      const sources = Array.isArray(payload.sources) ? payload.sources : [];
      if (sources.length) dataSources.value = sources;
      activeDataSource.value = payload.current || activeDataSource.value;
    } catch {
      dataSources.value = dataSources.value.length ? dataSources.value : DEFAULT_DATA_SOURCES;
    }
  }

  async function switchDataSource(nextSource) {
    if (!nextSource || nextSource === activeDataSource.value || switchingDataSource.value) return;
    switchingDataSource.value = true;
    dataSourceError.value = "";
    try {
      await switchDataSourceApi(nextSource);
      activeDataSource.value = nextSource;
      snapshot.value = null;
      replayToken.value += 1;
      await loadDataSources();
      await refresh({ force: true });
      window.setTimeout(() => {
        replayToken.value += 1;
      }, 40);
    } catch {
      dataSourceError.value = "数据源切换接口暂不可用，请重启实时服务后再切换。";
    } finally {
      switchingDataSource.value = false;
    }
  }

  onBeforeUnmount(() => {
    stopTimer();
  });

  return {
    snapshot,
    connected,
    replaying,
    paused,
    speed,
    replayToken,
    dataSources,
    activeDataSource,
    switchingDataSource,
    dataSourceError,
    graphView,
    start,
    setPaused,
    setSpeed,
    setGraphView,
    replay,
    switchDataSource,
    meta: computed(() => snapshot.value?.meta ?? {}),
    summary: computed(() => snapshot.value?.summary ?? {}),
    topNodes: computed(() => snapshot.value?.topNodes ?? []),
    recentEvents: computed(() => snapshot.value?.recentEvents ?? []),
    lastEvent: computed(() => snapshot.value?.lastEvent ?? null),
    fraudScripts: computed(() => snapshot.value?.fraudScripts ?? []),
  };
}
