from __future__ import annotations


GRAPH_STREAM_HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>DGraph-Fin 实时动态图检测</title>
  <style>
    :root {
      --bg: #101415;
      --panel: rgba(246, 242, 232, 0.92);
      --panel-dark: rgba(18, 26, 27, 0.88);
      --ink: #121819;
      --muted: #697472;
      --line: rgba(18, 24, 25, 0.16);
      --green: #1f7a62;
      --teal: #48a58d;
      --blue: #2e6d8f;
      --amber: #bc7a1b;
      --red: #c43b32;
      --paper: #f4efe2;
      --white: #fffdf6;
      --shadow: 0 22px 60px rgba(8, 12, 12, 0.24);
      --serif-bold: "Source Han Serif SC", "Noto Serif CJK SC", "思源宋体", "SimSun", serif;
      --latin-number: "Times New Roman", Times, serif;
      font-family: "Microsoft YaHei", "Segoe UI", Arial, sans-serif;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      min-height: 100vh;
      color: var(--ink);
      background:
        radial-gradient(circle at 12% 12%, rgba(72, 165, 141, 0.18), transparent 30%),
        radial-gradient(circle at 88% 18%, rgba(188, 122, 27, 0.14), transparent 28%),
        linear-gradient(135deg, #eef2ea 0%, #f7efdf 52%, #e9f0ed 100%);
    }

    body::before {
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      background:
        linear-gradient(90deg, rgba(16, 20, 21, 0.04) 1px, transparent 1px),
        linear-gradient(rgba(16, 20, 21, 0.04) 1px, transparent 1px);
      background-size: 42px 42px;
      mask-image: linear-gradient(to bottom, rgba(0,0,0,0.88), rgba(0,0,0,0.25));
    }

    .shell {
      position: relative;
      width: min(1500px, calc(100vw - 32px));
      height: 100vh;
      margin: 0 auto;
      padding: 8px 0 0;
      display: grid;
      grid-template-rows: auto minmax(0, 1fr);
      gap: 8px;
      overflow: hidden;
    }

    .topbar,
    .metric,
    .panel,
    .event-item,
    .node-row {
      border: 1px solid var(--line);
      background: var(--panel);
      box-shadow: var(--shadow);
      backdrop-filter: blur(16px);
    }

    .topbar {
      min-height: 44px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 7px 12px;
      border-radius: 12px;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 9px;
      min-width: 0;
    }

    .brand-mark {
      width: 30px;
      height: 30px;
      display: grid;
      place-items: center;
      border-radius: 8px;
      color: var(--white);
      background: linear-gradient(135deg, var(--green), var(--blue));
      font-family: var(--latin-number);
      font-weight: 800;
      letter-spacing: 0;
      font-size: 0.82rem;
    }

    .brand strong,
    .brand span {
      display: block;
    }

    .brand strong {
      font-size: 0.92rem;
      font-family: var(--serif-bold);
      font-weight: 700;
      line-height: 1.1;
    }

    .brand span,
    .top-meta span,
    .metric span,
    .panel-head span,
    .event-item span,
    .node-row span {
      color: var(--muted);
      font-size: 0.78rem;
    }

    .brand span {
      max-width: 520px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .top-meta {
      display: flex;
      justify-content: flex-end;
      flex-wrap: wrap;
      gap: 7px;
    }

    .top-meta span {
      min-height: 28px;
      display: inline-flex;
      align-items: center;
      padding: 0 9px;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: rgba(255, 253, 246, 0.7);
    }

    .main-grid {
      min-height: 0;
      display: grid;
      grid-template-columns: minmax(0, 1.45fr) minmax(360px, 0.55fr);
      gap: 10px;
      overflow: hidden;
    }

    .left {
      min-height: 0;
      display: grid;
      grid-template-rows: auto minmax(0, 1fr) 156px;
      gap: 10px;
    }

    .metrics {
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 8px;
    }

    .metric {
      min-height: 76px;
      padding: 10px 12px;
      border-radius: 12px;
      position: relative;
      overflow: hidden;
      transition: transform 240ms ease, border-color 240ms ease, box-shadow 240ms ease;
      animation: panel-in 520ms ease both;
    }

    .metric::after {
      content: "";
      position: absolute;
      inset: 0;
      pointer-events: none;
      opacity: 0;
      background: linear-gradient(90deg, transparent, rgba(72, 165, 141, 0.18), transparent);
      transform: translateX(-110%);
    }

    .metric:hover {
      transform: translateY(-2px);
      border-color: rgba(31, 122, 98, 0.28);
    }

    .metric.flash::after {
      animation: metric-sweep 680ms ease;
    }

    .metric strong {
      display: block;
      margin-top: 5px;
      font-family: var(--latin-number);
      font-size: clamp(1.18rem, 2vw, 1.85rem);
      letter-spacing: 0;
    }

    .metric small {
      display: block;
      margin-top: 4px;
      color: var(--muted);
      line-height: 1.25;
    }

    .graph-panel {
      position: relative;
      min-height: 0;
      overflow: hidden;
      border-radius: 18px;
      background:
        radial-gradient(circle at 52% 45%, rgba(72, 165, 141, 0.22), transparent 32%),
        radial-gradient(circle at 80% 25%, rgba(196, 59, 50, 0.12), transparent 24%),
        #121a1b;
      box-shadow: var(--shadow);
    }

    .graph-panel::before,
    .graph-panel::after {
      content: "";
      position: absolute;
      inset: 0;
      pointer-events: none;
      z-index: 2;
    }

    .graph-panel::before {
      opacity: 0.48;
      background:
        linear-gradient(120deg, transparent 0%, rgba(255, 253, 246, 0.08) 45%, transparent 58%),
        repeating-linear-gradient(0deg, transparent 0 18px, rgba(255, 253, 246, 0.028) 19px 20px);
      transform: translateX(-110%);
      animation: scan-sweep 7.2s linear infinite;
    }

    .graph-panel::after {
      border: 1px solid rgba(255, 253, 246, 0.08);
      box-shadow: inset 0 0 70px rgba(72, 165, 141, 0.08);
    }

    #graph-canvas {
      position: relative;
      z-index: 1;
      display: block;
      width: 100%;
      height: 100%;
      min-height: 0;
      cursor: grab;
      touch-action: none;
      user-select: none;
    }

    #graph-canvas.dragging {
      cursor: grabbing;
    }

    .graph-overlay {
      position: absolute;
      left: 16px;
      right: 16px;
      bottom: 16px;
      z-index: 3;
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 12px;
      pointer-events: none;
    }

    .legend,
    .progress {
      border: 1px solid rgba(255, 253, 246, 0.16);
      border-radius: 14px;
      background: rgba(18, 26, 27, 0.72);
      color: #e8efe9;
      padding: 11px 12px;
    }

    .legend {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      align-items: center;
    }

    .legend-item {
      display: inline-flex;
      align-items: center;
      gap: 7px;
      color: #dce6e0;
      font-size: 0.84rem;
    }

    .dot {
      width: 10px;
      height: 10px;
      border-radius: 999px;
      background: var(--color);
      box-shadow: 0 0 16px var(--color);
    }

    .progress {
      min-width: 260px;
      display: grid;
      gap: 8px;
    }

    .progress-head {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      font-family: var(--latin-number);
      font-size: 0.82rem;
    }

    .track {
      height: 8px;
      overflow: hidden;
      border-radius: 999px;
      background: rgba(255, 253, 246, 0.16);
    }

    .track i {
      display: block;
      width: calc(var(--progress, 0) * 100%);
      height: 100%;
      border-radius: inherit;
      background: linear-gradient(90deg, var(--teal), var(--amber), var(--red));
    }

    .side {
      min-height: 0;
      display: grid;
      grid-template-rows: minmax(176px, 0.28fr) minmax(0, 0.37fr) minmax(0, 0.35fr);
      gap: 10px;
      overflow: hidden;
    }

    .panel {
      display: grid;
      grid-template-rows: auto minmax(0, 1fr);
      min-height: 0;
      padding: 12px;
      border-radius: 14px;
      overflow: hidden;
      animation: panel-in 560ms ease both;
    }

    .panel.dark {
      background: var(--panel-dark);
      color: var(--white);
      border-color: rgba(255, 253, 246, 0.14);
    }

    .panel-head {
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 10px;
    }

    .panel-head h2 {
      margin: 0;
      font-size: 1rem;
      font-family: var(--serif-bold);
      font-weight: 700;
    }

    .risk-summary {
      display: grid;
      grid-template-rows: auto minmax(0, 1fr);
      gap: 12px;
      align-content: start;
    }

    .risk-summary-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 9px;
    }

    .risk-chip {
      min-height: 58px;
      padding: 10px;
      border: 1px solid rgba(18, 24, 25, 0.12);
      border-radius: 12px;
      background: rgba(255, 253, 246, 0.72);
    }

    .risk-chip span {
      display: block;
      color: var(--muted);
      font-size: 0.78rem;
    }

    .risk-chip strong {
      display: block;
      margin-top: 5px;
      font-family: var(--latin-number);
      font-size: 1.36rem;
      line-height: 1;
    }

    .event-stream,
    .node-list {
      display: grid;
      align-content: start;
      gap: 9px;
      min-height: 0;
      max-height: none;
      overflow: auto;
      padding-right: 4px;
      overscroll-behavior: contain;
    }

    .event-item,
    .node-row {
      box-shadow: none;
      border-radius: 12px;
      padding: 11px;
      animation: row-enter 360ms ease both;
      transition: transform 180ms ease, border-color 180ms ease, background 180ms ease;
    }

    .event-item {
      background: rgba(255, 253, 246, 0.78);
    }

    .event-item:first-child {
      border-color: rgba(188, 122, 27, 0.32);
      animation: row-enter 360ms ease both, first-event-glow 1.1s ease;
    }

    .event-item:hover,
    .node-row:hover {
      transform: translateX(2px);
    }

    .event-item strong,
    .node-row strong {
      display: flex;
      justify-content: space-between;
      gap: 10px;
      margin: 5px 0;
      font-family: var(--latin-number);
      letter-spacing: 0;
    }

    strong,
    b {
      font-family: var(--serif-bold);
      font-weight: 700;
    }

    .brand-mark,
    .metric strong,
    .progress-head,
    .event-item strong,
    .node-row strong,
    .bar-row strong {
      font-family: var(--latin-number);
    }

    .latin-number {
      font-family: var(--latin-number);
    }

    .serif-strong {
      font-family: var(--serif-bold);
      font-weight: 700;
    }

    .node-row {
      background: rgba(255, 253, 246, 0.08);
      border-color: rgba(255, 253, 246, 0.14);
      color: #f0f6f2;
    }

    .node-row:first-child {
      border-color: rgba(217, 75, 66, 0.32);
    }

    .node-row span {
      color: #aebdb7;
    }

    .bar-list {
      display: grid;
      gap: 8px;
      margin-top: 10px;
    }

    .bar-row {
      display: grid;
      grid-template-columns: 80px minmax(0, 1fr) 42px;
      align-items: center;
      gap: 8px;
      color: var(--muted);
      font-size: 0.8rem;
    }

    .bar-row .track {
      height: 7px;
      background: rgba(18, 24, 25, 0.1);
    }

    .bar-row .track i {
      background: var(--bar-color);
      transition: width 520ms ease;
    }

    .explain-panel {
      min-height: 0;
      display: grid;
      grid-template-columns: minmax(220px, 0.36fr) minmax(0, 1fr);
      gap: 12px;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 14px;
      background:
        linear-gradient(135deg, rgba(255, 253, 246, 0.94), rgba(236, 244, 239, 0.9)),
        var(--panel);
      box-shadow: var(--shadow);
      overflow: hidden;
      animation: panel-in 620ms ease both;
    }

    .explain-main {
      min-width: 0;
      display: grid;
      align-content: center;
      gap: 9px;
    }

    .explain-kicker,
    .explain-formula,
    .explain-meta,
    .explain-row span {
      color: var(--muted);
      font-size: 0.82rem;
      line-height: 1.45;
    }

    .explain-title {
      margin: 0;
      font-family: var(--serif-bold);
      font-size: 1.02rem;
      font-weight: 700;
    }

    .explain-score-line {
      display: flex;
      align-items: baseline;
      gap: 10px;
      flex-wrap: wrap;
    }

    .explain-score {
      font-family: var(--latin-number);
      font-size: clamp(1.8rem, 3vw, 2.8rem);
      line-height: 1;
    }

    .explain-level {
      min-height: 28px;
      display: inline-flex;
      align-items: center;
      padding: 0 10px;
      border-radius: 999px;
      color: var(--white);
      background: var(--level-color, var(--green));
      font-family: var(--serif-bold);
      font-weight: 700;
      font-size: 0.84rem;
    }

    .explain-bars {
      min-width: 0;
      display: grid;
      align-content: center;
      gap: 8px;
      overflow: hidden;
    }

    .explain-row {
      display: grid;
      grid-template-columns: 96px minmax(0, 1fr) 54px;
      align-items: center;
      gap: 9px;
    }

    .explain-row strong {
      font-family: var(--serif-bold);
      font-size: 0.84rem;
      font-weight: 700;
      white-space: nowrap;
    }

    .explain-row .track {
      height: 9px;
      background: rgba(18, 24, 25, 0.1);
    }

    .explain-row .track i {
      background: linear-gradient(90deg, rgba(72, 165, 141, 0.75), var(--bar-color, var(--green)));
      transition: width 520ms ease;
    }

    .explain-row em {
      color: var(--muted);
      font-family: var(--latin-number);
      font-style: normal;
      text-align: right;
      font-size: 0.86rem;
    }

    @keyframes panel-in {
      from {
        opacity: 0;
        transform: translateY(8px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }

    @keyframes row-enter {
      from {
        opacity: 0;
        transform: translateY(-5px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }

    @keyframes metric-sweep {
      0% {
        opacity: 0;
        transform: translateX(-110%);
      }
      35% {
        opacity: 1;
      }
      100% {
        opacity: 0;
        transform: translateX(110%);
      }
    }

    @keyframes first-event-glow {
      0% {
        box-shadow: 0 0 0 rgba(188, 122, 27, 0);
      }
      35% {
        box-shadow: 0 0 26px rgba(188, 122, 27, 0.22);
      }
      100% {
        box-shadow: 0 0 0 rgba(188, 122, 27, 0);
      }
    }

    @keyframes scan-sweep {
      0% {
        transform: translateX(-112%);
      }
      46% {
        transform: translateX(112%);
      }
      100% {
        transform: translateX(112%);
      }
    }

    @media (prefers-reduced-motion: reduce) {
      *,
      *::before,
      *::after {
        animation-duration: 1ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 1ms !important;
      }
    }

    @media (max-width: 1120px) {
      .main-grid,
      .side {
        grid-template-columns: 1fr;
        grid-template-rows: auto;
        height: auto;
        min-height: 0;
        overflow: visible;
      }

      .metrics {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }

      .left,
      .explain-panel {
        grid-template-columns: 1fr;
        grid-template-rows: auto;
      }

      .graph-panel {
        min-height: 520px;
      }
    }

    @media (max-width: 720px) {
      .shell { width: min(100% - 20px, 1500px); }
      .topbar,
      .graph-overlay,
      .risk-summary {
        grid-template-columns: 1fr;
        flex-direction: column;
        align-items: stretch;
      }
      .metrics { grid-template-columns: 1fr; }
      .progress { min-width: 0; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <header class="topbar">
      <div class="brand">
        <div class="brand-mark">DG</div>
        <div>
          <strong>DGraph-Fin 动态交易图</strong>
          <span>按时间戳逐条进件，实时构建节点网络并识别疑似欺诈节点</span>
        </div>
      </div>
      <div class="top-meta">
        <span id="mode">准备启动</span>
        <span id="clock">--</span>
        <span id="throughput">-- 笔/秒</span>
      </div>
    </header>

    <main class="main-grid">
      <section class="left">
        <div class="metrics">
          <article class="metric"><span>窗口交易</span><strong id="m-events">0</strong><small>最近窗口内的交易数</small></article>
          <article class="metric"><span>窗口节点</span><strong id="m-active">0</strong><small>最近窗口内仍活跃的节点</small></article>
          <article class="metric"><span>疑似欺诈节点</span><strong id="m-fraud">0</strong><small>当前窗口命中的风险节点</small></article>
          <article class="metric"><span>窗口高危事件</span><strong id="m-critical">0</strong><small>当前窗口内的冻结复核事件</small></article>
          <article class="metric"><span>可视边窗口</span><strong id="m-edges">0</strong><small>最近窗口内的交易关系</small></article>
        </div>

        <section class="graph-panel" aria-label="动态图交易网络">
          <canvas id="graph-canvas"></canvas>
          <div class="graph-overlay">
            <div class="legend">
              <span class="legend-item"><i class="dot" style="--color:#45b591"></i>低风险节点</span>
              <span class="legend-item"><i class="dot" style="--color:#d18b24"></i>复核节点</span>
              <span class="legend-item"><i class="dot" style="--color:#d94b42"></i>疑似欺诈节点</span>
              <span class="legend-item"><i class="dot" style="--color:#8fa0a0"></i>背景节点</span>
            </div>
            <div class="progress">
              <div class="progress-head"><span id="progress-label">0 / 0</span><span id="timestamp-label">时间戳 --</span></div>
              <div class="track" style="--progress:0"><i id="progress-bar"></i></div>
            </div>
          </div>
        </section>

        <section class="explain-panel" aria-label="节点风险判定依据">
          <div class="explain-main">
            <div class="explain-kicker">当前焦点节点</div>
            <h2 id="explain-node" class="explain-title">等待交易进入</h2>
            <div class="explain-score-line">
              <strong id="explain-score" class="explain-score">--</strong>
              <span id="explain-level" class="explain-level">--</span>
            </div>
            <div id="explain-formula" class="explain-formula">系统将在交易进入后展示模型先验与动态行为贡献。</div>
            <div id="explain-meta" class="explain-meta">--</div>
          </div>
          <div id="explain-bars" class="explain-bars"></div>
        </section>

      </section>

      <aside class="side">
        <section class="panel">
          <div class="panel-head"><h2>风险统计</h2><span>当前窗口</span></div>
          <div class="risk-summary">
            <div class="risk-summary-grid">
              <div class="risk-chip"><span>严重风险</span><strong id="risk-critical">0</strong></div>
              <div class="risk-chip"><span>高危风险</span><strong id="risk-high">0</strong></div>
              <div class="risk-chip"><span>中危风险</span><strong id="risk-medium">0</strong></div>
              <div class="risk-chip"><span>低危风险</span><strong id="risk-low">0</strong></div>
            </div>
            <div class="bar-list" id="level-bars"></div>
          </div>
        </section>

        <section class="panel dark">
          <div class="panel-head"><h2>高风险节点榜</h2><span>实时更新</span></div>
          <div class="node-list" id="node-list"></div>
        </section>

        <section class="panel">
          <div class="panel-head"><h2>交易流</h2><span>最近事件</span></div>
          <div class="event-stream" id="event-stream"></div>
        </section>
      </aside>
    </main>
  </div>

  <script>
    const state = {
      nodes: new Map(),
      snapshot: null,
      view: { rotX: -0.24, rotY: 0.58, zoom: 1.16 },
      drag: { active: false, pointerId: null, startX: 0, startY: 0, originRotX: 0, originRotY: 0 },
      previousMetrics: new Map(),
      latestEventId: null,
      latestFocusNode: null,
      lastRenderAt: performance.now(),
      renderKeys: { bars: "", nodes: "", events: "" },
    };
    const levelColor = { critical: "#c43b32", high: "#bc7a1b", medium: "#2e6d8f", low: "#1f7a62" };
    const levelText = { critical: "严重", high: "高危", medium: "中危", low: "低危" };
    const truthText = { fraud: "欺诈样本", normal: "正常样本", background: "背景节点" };
    const channelText = {
      wallet: "钱包",
      bank_app: "银行应用",
      qr_pay: "扫码支付",
      web: "网页",
      merchant_api: "商户接口",
      node_probe: "节点探测",
    };
    const nodeColor = (node) => {
      if (node.riskLevel === "critical" || node.riskLevel === "high") return "#d94b42";
      if (node.riskLevel === "medium") return "#d18b24";
      if (node.groundTruth === "background") return "#8fa0a0";
      return "#45b591";
    };
    const formatNumber = (value) => new Intl.NumberFormat("zh-CN").format(Number(value || 0));
    const formatScore = (value) => Number.isFinite(Number(value)) ? Number(value).toFixed(4) : "--";
    const riskLabel = (level) => levelText[level] || "未知";
    const truthLabel = (label) => truthText[label] || "未知样本";
    const channelLabel = (channel) => channelText[channel] || String(channel || "未知渠道");

    function roundedRect(ctx, x, y, width, height, radius) {
      const r = Math.min(radius, width / 2, height / 2);
      ctx.moveTo(x + r, y);
      ctx.lineTo(x + width - r, y);
      ctx.quadraticCurveTo(x + width, y, x + width, y + r);
      ctx.lineTo(x + width, y + height - r);
      ctx.quadraticCurveTo(x + width, y + height, x + width - r, y + height);
      ctx.lineTo(x + r, y + height);
      ctx.quadraticCurveTo(x, y + height, x, y + height - r);
      ctx.lineTo(x, y + r);
      ctx.quadraticCurveTo(x, y, x + r, y);
    }

    function stableUnit(nodeId, salt) {
      const value = Math.sin((Number(nodeId) + salt) * 12.9898) * 43758.5453;
      return value - Math.floor(value);
    }

    function ensureCloudPoint(node) {
      const existing = state.nodes.get(node.id) || {};
      if (existing.cloud) return existing.cloud;
      const theta = stableUnit(node.id, 1.7) * Math.PI * 2;
      const phi = Math.acos(2 * stableUnit(node.id, 9.3) - 1);
      const radius = 0.82 + stableUnit(node.id, 4.1) * 1.06;
      const clusterBias = (node.riskScore - 0.36) * 0.18;
      const band = Math.floor(stableUnit(node.id, 12.8) * 5) - 2;
      const lateralSpread = (stableUnit(node.id, 21.6) - 0.5) * 0.72;
      const verticalSpread = band * 0.18 + (stableUnit(node.id, 6.4) - 0.5) * 0.22;
      return {
        x: Math.sin(phi) * Math.cos(theta) * radius + clusterBias + lateralSpread,
        y: Math.cos(phi) * radius * 0.78 + verticalSpread,
        z: Math.sin(phi) * Math.sin(theta) * radius - clusterBias * 0.3 + (stableUnit(node.id, 31.3) - 0.5) * 0.64,
      };
    }

    function projectPoint(point, width, height) {
      const cosY = Math.cos(state.view.rotY);
      const sinY = Math.sin(state.view.rotY);
      const cosX = Math.cos(state.view.rotX);
      const sinX = Math.sin(state.view.rotX);
      const x1 = point.x * cosY - point.z * sinY;
      const z1 = point.x * sinY + point.z * cosY;
      const y1 = point.y * cosX - z1 * sinX;
      const z2 = point.y * sinX + z1 * cosX;
      const depth = z2 + 3.15;
      const perspective = (0.92 / depth) * state.view.zoom;
      const scale = Math.min(width, height) * 1.08;
      return {
        x: width * 0.54 + x1 * scale * perspective,
        y: height * 0.5 + y1 * scale * perspective,
        z: z2,
        depth,
        perspective,
        alpha: Math.max(0.2, Math.min(1, 1.1 - depth * 0.18)),
      };
    }

    function updateNodeLayout(nodes, width, height) {
      const now = performance.now();
      nodes.forEach((node, index) => {
        const existing = state.nodes.get(node.id) || {};
        const cloud = ensureCloudPoint(node);
        const bornAt = existing.bornAt || now;
        const drift = Date.now() * 0.00012 + index * 0.07;
        const animatedCloud = {
          x: cloud.x + Math.sin(drift + node.riskScore * 2) * 0.018,
          y: cloud.y + Math.cos(drift * 1.2) * 0.014,
          z: cloud.z + Math.sin(drift * 0.8) * 0.018,
        };
        const projected = projectPoint(animatedCloud, width, height);
        state.nodes.set(node.id, { ...node, ...projected, cloud, bornAt });
      });
    }

    function drawGraph() {
      const canvas = document.getElementById("graph-canvas");
      const ctx = canvas.getContext("2d");
      const rect = canvas.getBoundingClientRect();
      const ratio = window.devicePixelRatio || 1;
      const width = Math.max(1, Math.floor(rect.width * ratio));
      const height = Math.max(1, Math.floor(rect.height * ratio));
      if (canvas.width !== width || canvas.height !== height) {
        canvas.width = width;
        canvas.height = height;
      }
      ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
      ctx.clearRect(0, 0, rect.width, rect.height);
      if (!state.snapshot) {
        requestAnimationFrame(drawGraph);
        return;
      }
      const nodes = state.snapshot.nodes || [];
      const edges = state.snapshot.edges || [];
      const latestEvent = state.snapshot.lastEvent || {};
      const animationClock = performance.now();
      updateNodeLayout(nodes, rect.width, rect.height);
      const visible = new Set(nodes.map((node) => node.id));
      const cx = rect.width * 0.5;
      const cy = rect.height * 0.5;

      const gradient = ctx.createRadialGradient(cx, rect.height * 0.45, 0, cx, cy, Math.min(rect.width, rect.height) * 0.72);
      gradient.addColorStop(0, "rgba(72,165,141,0.18)");
      gradient.addColorStop(1, "rgba(18,26,27,0)");
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, rect.width, rect.height);

      edges.forEach((edge) => {
        if (!visible.has(edge.source) || !visible.has(edge.target)) return;
        const a = state.nodes.get(edge.source);
        const b = state.nodes.get(edge.target);
        if (!a || !b) return;
        const risky = edge.riskLevel === "critical" || edge.riskLevel === "high";
        const medium = edge.riskLevel === "medium";
        const depthAlpha = Math.max(0.18, Math.min(0.72, (a.alpha + b.alpha) * 0.5));
        const lowAlpha = 0.12 * depthAlpha;
        const mediumAlpha = 0.34 * depthAlpha;
        const riskAlpha = 0.58 * depthAlpha;
        const lineGradient = ctx.createLinearGradient(a.x, a.y, b.x, b.y);
        lineGradient.addColorStop(0, risky ? `rgba(217,75,66,${riskAlpha})` : medium ? `rgba(209,139,36,${mediumAlpha})` : `rgba(220,232,226,${lowAlpha})`);
        lineGradient.addColorStop(1, risky ? `rgba(188,122,27,${riskAlpha * 0.9})` : medium ? `rgba(72,165,141,${mediumAlpha * 0.86})` : `rgba(72,165,141,${lowAlpha * 0.82})`);
        ctx.strokeStyle = lineGradient;
        ctx.lineWidth = edge.riskLevel === "critical" ? 1.15 : risky ? 0.92 : medium ? 0.64 : 0.46;
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.stroke();
      });

      const projectedNodes = [...nodes]
        .map((node) => ({ node, point: state.nodes.get(node.id) }))
        .filter((item) => item.point)
        .sort((a, b) => b.point.depth - a.point.depth);
      const rankedNodes = [...nodes].sort((a, b) => b.riskScore - a.riskScore);
      projectedNodes.forEach(({ node, point }) => {
        const color = nodeColor(node);
        const riskWeight = Math.max(0, Math.min(1, node.riskScore));
        const age = Math.min(1, (animationClock - (point.bornAt || animationClock)) / 900);
        const entryScale = 0.48 + age * 0.52;
        const levelBoost = node.riskLevel === "critical" ? 1.55 : node.riskLevel === "high" ? 1.35 : node.riskLevel === "medium" ? 1.12 : 0.68;
        const baseRadius = 1.05 + Math.min(node.degree, 28) * 0.035 + Math.pow(riskWeight, 1.55) * 7.4;
        const radius = baseRadius * levelBoost * Math.max(0.46, point.perspective * 1.56) * entryScale;
        const nodeAlpha = Math.min(1, Math.max(0.12, point.alpha * (0.24 + riskWeight * 0.86)));
        const shadowBlur = node.riskLevel === "critical" ? 30 : node.riskLevel === "high" ? 24 : node.riskLevel === "medium" ? 14 : 3;
        ctx.beginPath();
        ctx.fillStyle = color;
        ctx.shadowColor = color;
        ctx.shadowBlur = shadowBlur;
        ctx.globalAlpha = nodeAlpha;
        ctx.arc(point.x, point.y, radius, 0, Math.PI * 2);
        ctx.fill();
        ctx.globalAlpha = 1;
        ctx.shadowBlur = 0;
        ctx.lineWidth = node.detectedFraud ? 1.9 : node.riskLevel === "medium" ? 1.1 : 0.45;
        ctx.strokeStyle = node.detectedFraud ? "rgba(255,253,246,0.86)" : node.riskLevel === "medium" ? "rgba(255,253,246,0.46)" : "rgba(255,253,246,0.18)";
        ctx.stroke();
      });

      rankedNodes.slice(0, 6).forEach((node) => {
        const point = state.nodes.get(node.id);
        if (!point || node.riskScore < 0.35) return;
        const label = `${node.id}  ${formatScore(node.riskScore)}`;
        ctx.font = "12px Times New Roman, Times, serif";
        const width = ctx.measureText(label).width + 14;
        const x = Math.min(Math.max(point.x + 10, 8), rect.width - width - 8);
        const y = Math.min(Math.max(point.y - 24, 8), rect.height - 28);
        ctx.fillStyle = "rgba(18,26,27,0.76)";
        ctx.strokeStyle = "rgba(255,253,246,0.16)";
        ctx.lineWidth = 1;
        ctx.beginPath();
        roundedRect(ctx, x, y, width, 22, 8);
        ctx.fill();
        ctx.stroke();
        ctx.fillStyle = node.detectedFraud ? "#ffd4cf" : "#e6f3ec";
        ctx.fillText(label, x + 7, y + 15);
      });

      requestAnimationFrame(drawGraph);
    }

    function renderBars(summary) {
      const levels = [
        ["critical", summary.criticalCount || 0],
        ["high", summary.highCount || 0],
        ["medium", summary.mediumCount || 0],
        ["low", summary.lowCount || 0],
      ];
      levels.forEach(([level, count]) => {
        const element = document.getElementById(`risk-${level}`);
        if (element) {
          element.textContent = formatNumber(count);
          element.style.color = levelColor[level] || "#1f7a62";
        }
      });
      const nextKey = levels.map(([level, count]) => `${level}:${count}`).join("|");
      if (state.renderKeys.bars === nextKey) return;
      state.renderKeys.bars = nextKey;
      const maxValue = Math.max(1, ...levels.map((item) => item[1]));
      document.getElementById("level-bars").innerHTML = levels.map(([level, count]) => `
        <div class="bar-row">
          <span>${riskLabel(level)}</span>
          <div class="track" style="--progress:${count / maxValue}; --bar-color:${levelColor[level]}"><i></i></div>
          <strong>${formatNumber(count)}</strong>
        </div>
      `).join("");
    }

    function renderNodeList(nodes) {
      const list = nodes || [];
      const nextKey = list.map((node) => `${node.id}:${node.riskLevel}:${Number(node.riskScore).toFixed(4)}:${node.degree}:${node.eventCount}`).join("|");
      if (state.renderKeys.nodes === nextKey) return;
      state.renderKeys.nodes = nextKey;
      document.getElementById("node-list").innerHTML = list.map((node) => `
        <article class="node-row">
          <span>${node.detectedFraud ? "疑似欺诈节点" : "观察节点"} / ${truthLabel(node.groundTruth)}</span>
          <strong><b class="latin-number">${node.id}</b><b style="color:${levelColor[node.riskLevel] || "#45b591"}"><span class="serif-strong">${riskLabel(node.riskLevel)}</span> <span class="latin-number">${formatScore(node.riskScore)}</span></b></strong>
          <span>度 ${node.degree} / 事件 ${node.eventCount} / 静态先验 ${formatScore(node.staticScore)}</span>
        </article>
      `).join("");
    }

    function renderEventStream(events) {
      const list = events || [];
      const nextKey = list.map((event) => `${event.eventId}:${event.riskLevel}:${Number(event.riskScore).toFixed(4)}`).join("|");
      if (state.renderKeys.events === nextKey) return;
      state.renderKeys.events = nextKey;
      document.getElementById("event-stream").innerHTML = list.map((event) => `
        <article class="event-item">
          <span>时间戳 ${event.timestamp} / ${channelLabel(event.channel)}</span>
          <strong><b class="latin-number">${event.srcNode} -> ${event.dstNode}</b><b class="serif-strong" style="color:${levelColor[event.riskLevel] || "#1f7a62"}">${riskLabel(event.riskLevel)}</b></strong>
          <span>风险分 ${formatScore(event.riskScore)} / 焦点节点 ${event.focusNode} / 金额 ${Number(event.amount).toFixed(2)}</span>
        </article>
      `).join("");
    }

    function renderExplanation(snapshot) {
      const latest = snapshot.lastEvent;
      const detail = latest?.focusNodeDetail || null;
      const breakdown = detail?.scoreBreakdown || null;
      const nodeTitle = document.getElementById("explain-node");
      const scoreEl = document.getElementById("explain-score");
      const levelEl = document.getElementById("explain-level");
      const formulaEl = document.getElementById("explain-formula");
      const metaEl = document.getElementById("explain-meta");
      const barsEl = document.getElementById("explain-bars");

      if (!detail || !breakdown) {
        nodeTitle.textContent = "等待交易进入";
        scoreEl.textContent = "--";
        levelEl.textContent = "--";
        formulaEl.textContent = "系统将在交易进入后展示模型先验与动态行为贡献。";
        metaEl.textContent = "--";
        barsEl.innerHTML = "";
        return;
      }

      const level = breakdown.riskLevel || detail.riskLevel;
      const metrics = breakdown.metrics || {};
      nodeTitle.textContent = `节点 ${detail.id} 的风险判定`;
      scoreEl.textContent = formatScore(breakdown.finalScore);
      scoreEl.style.color = levelColor[level] || "#1f7a62";
      levelEl.textContent = riskLabel(level);
      levelEl.style.setProperty("--level-color", levelColor[level] || "#1f7a62");
      formulaEl.textContent = breakdown.formula || "综合风险分由静态模型先验和实时交易行为加权得到，条形表示该项特征强度，数字表示加权后的得分贡献。";
      metaEl.textContent = `度 ${formatNumber(metrics.degree)} / 事件 ${formatNumber(metrics.eventCount)} / 时间跨度 ${formatNumber(metrics.timeSpan)} / 渠道 ${formatNumber(metrics.channelCount)} 类 / 交易类型 ${formatNumber(metrics.edgeTypeCount)} 类`;
      barsEl.innerHTML = (breakdown.components || []).map((item) => {
        const contribution = Number(item.contribution || 0);
        const weight = Number(item.weight || 0);
        const width = weight > 0 ? Math.max(0, Math.min(1, contribution / weight)) : 0;
        const color = contribution >= 0.12 ? levelColor.critical : contribution >= 0.07 ? levelColor.high : contribution >= 0.035 ? levelColor.medium : levelColor.low;
        return `
          <div class="explain-row" title="${item.evidence || ""}">
            <strong>${item.label}</strong>
            <div class="track" style="--progress:${width}; --bar-color:${color}"><i></i></div>
            <em>${formatScore(contribution)}</em>
          </div>
        `;
      }).join("");
    }

    function setMetricValue(id, value) {
      const element = document.getElementById(id);
      const next = formatNumber(value);
      if (element.textContent !== next) {
        element.textContent = next;
        const metric = element.closest(".metric");
        if (metric) {
          metric.classList.remove("flash");
          void metric.offsetWidth;
          metric.classList.add("flash");
        }
      }
    }

    function render(snapshot) {
      state.snapshot = snapshot;
      const meta = snapshot.meta;
      const summary = snapshot.summary;
      const latest = snapshot.lastEvent;
      const isNewEvent = latest && latest.eventId !== state.latestEventId;
      if (isNewEvent) {
        state.latestEventId = latest.eventId;
        state.latestFocusNode = latest.focusNode;
      }
      document.getElementById("mode").textContent = meta.mode;
      document.getElementById("clock").textContent = new Date().toLocaleTimeString("zh-CN", { hour12: false });
      document.getElementById("throughput").textContent = `${formatScore(meta.eventsPerSecond)} 笔/秒`;
      setMetricValue("m-events", summary.windowEventCount);
      setMetricValue("m-active", summary.activeNodeCount);
      setMetricValue("m-fraud", summary.detectedFraudNodeCount);
      setMetricValue("m-critical", summary.criticalCount);
      setMetricValue("m-edges", summary.visibleEdgeCount);
      document.getElementById("progress-label").textContent = `${formatNumber(meta.position)} / ${formatNumber(meta.totalEvents)}`;
      document.getElementById("timestamp-label").textContent = `时间戳 ${meta.currentTimestamp ?? "--"}`;
      document.querySelector(".progress .track").style.setProperty("--progress", String(meta.progress || 0));
      renderBars(summary);
      renderNodeList(snapshot.topNodes);
      renderEventStream(snapshot.recentEvents);
      renderExplanation(snapshot);
    }

    function setupGraphInteractions() {
      const canvas = document.getElementById("graph-canvas");
      canvas.addEventListener("pointerdown", (event) => {
        state.drag.active = true;
        state.drag.pointerId = event.pointerId;
        state.drag.startX = event.clientX;
        state.drag.startY = event.clientY;
        state.drag.originRotX = state.view.rotX;
        state.drag.originRotY = state.view.rotY;
        canvas.classList.add("dragging");
        canvas.setPointerCapture(event.pointerId);
      });
      canvas.addEventListener("pointermove", (event) => {
        if (!state.drag.active || state.drag.pointerId !== event.pointerId) return;
        const deltaX = event.clientX - state.drag.startX;
        const deltaY = event.clientY - state.drag.startY;
        state.view.rotY = state.drag.originRotY + deltaX * 0.008;
        state.view.rotX = Math.max(-1.15, Math.min(1.15, state.drag.originRotX + deltaY * 0.006));
      });
      const endDrag = (event) => {
        if (!state.drag.active || state.drag.pointerId !== event.pointerId) return;
        state.drag.active = false;
        state.drag.pointerId = null;
        canvas.classList.remove("dragging");
        try {
          canvas.releasePointerCapture(event.pointerId);
        } catch (error) {
          // 指针可能已经被浏览器释放。
        }
      };
      canvas.addEventListener("pointerup", endDrag);
      canvas.addEventListener("pointercancel", endDrag);
      canvas.addEventListener("wheel", (event) => {
        event.preventDefault();
        const nextZoom = state.view.zoom * (event.deltaY > 0 ? 0.92 : 1.08);
        state.view.zoom = Math.max(0.52, Math.min(2.8, nextZoom));
      }, { passive: false });
      canvas.addEventListener("dblclick", () => {
        state.view.rotX = -0.24;
        state.view.rotY = 0.58;
        state.view.zoom = 1.16;
      });
    }

    async function refresh() {
      try {
        const response = await fetch("/api/graph-stream", { cache: "no-store" });
        if (!response.ok) return;
        render(await response.json());
      } catch (error) {
        document.getElementById("mode").textContent = "连接中断";
      }
    }

    setupGraphInteractions();
    drawGraph();
    refresh();
    setInterval(refresh, 650);
  </script>
</body>
</html>
"""
