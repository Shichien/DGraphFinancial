from __future__ import annotations


HTML_STYLE = """
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600;700&display=swap');

:root {
  --paper: #f5f2e8;
  --paper-strong: #fffdf6;
  --ink: #17201f;
  --muted: #69736f;
  --line: rgba(23, 32, 31, 0.14);
  --panel: rgba(255, 253, 246, 0.84);
  --panel-solid: #fffdf6;
  --green: #1f7a62;
  --green-soft: rgba(31, 122, 98, 0.12);
  --blue: #256b8f;
  --blue-soft: rgba(37, 107, 143, 0.12);
  --amber: #b36a13;
  --amber-soft: rgba(179, 106, 19, 0.14);
  --red: #b8322a;
  --red-soft: rgba(184, 50, 42, 0.14);
  --violet: #6850a8;
  --radius-lg: 18px;
  --radius-md: 12px;
  --radius-sm: 8px;
  --shadow: 0 18px 52px rgba(41, 36, 22, 0.14);
}

* {
  box-sizing: border-box;
}

html {
  scroll-behavior: smooth;
}

body {
  margin: 0;
  min-height: 100vh;
  color: var(--ink);
  background:
    linear-gradient(90deg, rgba(23, 32, 31, 0.05) 1px, transparent 1px),
    linear-gradient(rgba(23, 32, 31, 0.04) 1px, transparent 1px),
    linear-gradient(135deg, #f7f2e4 0%, #eef4ee 45%, #f8efe4 100%);
  background-size: 42px 42px, 42px 42px, auto;
  font-family: 'IBM Plex Sans', 'Microsoft YaHei', 'Segoe UI', sans-serif;
}

body::before {
  content: "";
  position: fixed;
  inset: 0;
  pointer-events: none;
  background:
    radial-gradient(circle at 18% 12%, rgba(31, 122, 98, 0.18), transparent 28%),
    radial-gradient(circle at 90% 18%, rgba(179, 106, 19, 0.14), transparent 26%),
    radial-gradient(circle at 70% 80%, rgba(37, 107, 143, 0.14), transparent 30%);
  opacity: 0.85;
}

.skip-link {
  position: absolute;
  left: 12px;
  top: -48px;
  z-index: 100;
  padding: 10px 14px;
  color: #fffdf6;
  background: var(--green);
  border-radius: 999px;
  transition: top 0.2s ease;
}

.skip-link:focus {
  top: 12px;
}

.shell {
  position: relative;
  width: min(1360px, calc(100vw - 40px));
  margin: 0 auto;
  padding: 24px 0 42px;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 18px;
}

.brand,
.topbar-meta,
.case-detail-head,
.stream-head {
  display: flex;
  align-items: center;
}

.brand {
  gap: 12px;
}

.brand-mark {
  width: 46px;
  height: 46px;
  display: grid;
  place-items: center;
  border-radius: 12px;
  color: #fffdf6;
  background: linear-gradient(135deg, var(--green), var(--blue));
  font-family: 'JetBrains Mono', Consolas, monospace;
  font-weight: 700;
}

.brand-copy strong,
.brand-copy span {
  display: block;
}

.brand-copy strong {
  font-size: 1rem;
}

.brand-copy span {
  color: var(--muted);
  font-size: 0.84rem;
}

.topbar-meta {
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 10px;
}

.pill {
  display: inline-flex;
  align-items: center;
  min-height: 36px;
  padding: 0 12px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: rgba(255, 253, 246, 0.68);
  color: var(--muted);
  font-size: 0.84rem;
}

main {
  display: grid;
  gap: 18px;
}

.hero {
  display: grid;
  grid-template-columns: minmax(0, 1.12fr) minmax(360px, 0.88fr);
  gap: 18px;
}

.hero-panel,
.stream-panel,
.investigation-panel {
  position: relative;
  overflow: hidden;
  border: 1px solid var(--line);
  border-radius: var(--radius-lg);
  background: var(--panel);
  box-shadow: var(--shadow);
  backdrop-filter: blur(18px);
}

.hero-panel {
  min-height: 438px;
  padding: 30px;
}

.hero-panel::after,
.stream-panel::after,
.investigation-panel::after {
  content: "";
  position: absolute;
  inset: 0;
  pointer-events: none;
  border-radius: inherit;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.72);
}

.eyebrow {
  display: inline-flex;
  align-items: center;
  padding: 8px 12px;
  border: 1px solid rgba(31, 122, 98, 0.22);
  border-radius: 999px;
  color: var(--green);
  background: var(--green-soft);
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.hero h1 {
  max-width: 10ch;
  margin: 18px 0 14px;
  font-size: clamp(3rem, 6vw, 6.5rem);
  line-height: 0.92;
  letter-spacing: 0;
}

.hero-intro {
  max-width: 62ch;
  margin: 0;
  color: #34413d;
  font-size: 1.03rem;
  line-height: 1.78;
}

.hero-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-top: 26px;
}

.hero-stat,
.policy-card,
.case-detail,
.case-process-item,
.audit-item,
.mini-stat {
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  background: rgba(255, 253, 246, 0.72);
}

.hero-stat {
  min-height: 124px;
  padding: 16px;
}

.hero-stat .label,
.mini-stat span,
.policy-card span,
.case-button span,
.audit-item span,
.case-process-item span,
.stream-head span,
.stream-head small {
  display: block;
  color: var(--muted);
  font-size: 0.78rem;
}

.hero-stat strong {
  display: block;
  margin-top: 8px;
  font-family: 'JetBrains Mono', Consolas, monospace;
  font-size: clamp(1.45rem, 2.8vw, 2.2rem);
}

.hero-stat small {
  display: block;
  margin-top: 8px;
  color: var(--muted);
  line-height: 1.48;
}

.signal-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 9px;
  margin-top: 22px;
}

.signal-chip {
  padding: 9px 11px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: rgba(255, 253, 246, 0.72);
  color: #34413d;
  font-size: 0.84rem;
}

.stream-panel {
  min-height: 438px;
  padding: 22px;
  display: grid;
  grid-template-rows: auto minmax(210px, 1fr) auto;
  gap: 12px;
}

.stream-head {
  justify-content: space-between;
  gap: 12px;
}

.stream-head strong {
  font-family: 'JetBrains Mono', Consolas, monospace;
  font-size: clamp(2rem, 4vw, 3.8rem);
}

#risk-3d {
  width: 100%;
  min-height: 230px;
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  background: #16201f;
}

.level-bars {
  display: grid;
  gap: 9px;
}

.level-row {
  display: grid;
  grid-template-columns: 82px minmax(0, 1fr) 44px;
  align-items: center;
  gap: 10px;
  color: var(--muted);
  font-size: 0.82rem;
}

.level-track {
  height: 9px;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(23, 32, 31, 0.1);
}

.level-track span {
  display: block;
  height: 100%;
  width: calc(var(--fill) * 100%);
  border-radius: inherit;
  background: var(--bar-color);
}

.section {
  margin: 0;
}

.section-head {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 18px;
  margin: 6px 0 12px;
}

.section-head h2 {
  margin: 0 0 7px;
  font-size: 1.12rem;
}

.section-head p {
  max-width: 76ch;
  margin: 0;
  color: var(--muted);
  line-height: 1.62;
}

.refresh-note {
  flex: 0 0 auto;
  color: var(--muted);
  font-family: 'JetBrains Mono', Consolas, monospace;
  font-size: 0.82rem;
}

.investigation-panel {
  padding: 18px;
}

.policy-grid {
  display: grid;
  grid-template-columns: 1fr 1.42fr 1fr;
  gap: 12px;
  margin-bottom: 14px;
}

.policy-card {
  min-height: 116px;
  padding: 15px;
}

.policy-card strong {
  display: block;
  margin-top: 6px;
  line-height: 1.35;
}

.threshold-list {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
  margin-top: 9px;
}

.threshold-item {
  min-height: 78px;
  padding: 9px;
  border-radius: var(--radius-sm);
  background: rgba(23, 32, 31, 0.04);
}

.threshold-item strong {
  font-family: 'JetBrains Mono', Consolas, monospace;
}

.investigation-layout {
  display: grid;
  grid-template-columns: minmax(290px, 0.38fr) minmax(0, 1fr);
  gap: 14px;
}

.case-list {
  display: grid;
  align-content: start;
  gap: 10px;
  max-height: 680px;
  overflow: auto;
  padding-right: 4px;
}

.case-button {
  display: grid;
  gap: 8px;
  width: 100%;
  min-height: 112px;
  padding: 14px;
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  color: inherit;
  background: rgba(255, 253, 246, 0.7);
  text-align: left;
  cursor: pointer;
  transition: transform 0.18s ease, border-color 0.18s ease, background 0.18s ease;
}

.case-button:hover,
.case-button:focus-visible,
.case-button.active {
  transform: translateY(-2px);
  border-color: rgba(31, 122, 98, 0.38);
  background: rgba(255, 253, 246, 0.96);
  outline: none;
}

.case-button strong {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  font-family: 'JetBrains Mono', Consolas, monospace;
}

.case-detail {
  min-height: 680px;
  padding: 18px;
  background: rgba(255, 253, 246, 0.78);
}

.case-detail-head {
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 14px;
}

.detail-kicker {
  display: block;
  margin-bottom: 7px;
  color: var(--green);
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.case-detail h3 {
  margin: 0;
  font-size: clamp(1.2rem, 2.8vw, 2rem);
}

.status-chip {
  display: inline-flex;
  align-items: center;
  min-height: 34px;
  padding: 0 11px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: rgba(255, 253, 246, 0.78);
  color: var(--muted);
  font-size: 0.82rem;
  white-space: nowrap;
}

.case-metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 12px;
}

.mini-stat {
  min-height: 86px;
  padding: 14px;
}

.mini-stat strong {
  display: block;
  margin-top: 7px;
  line-height: 1.32;
  word-break: break-word;
}

.case-process {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 12px;
}

.case-process-item {
  padding: 14px;
  line-height: 1.55;
}

.case-process-item span {
  margin-bottom: 7px;
}

.trace-canvas {
  min-height: 276px;
  margin-bottom: 12px;
  overflow: hidden;
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  background: #18211f;
}

.trace-canvas svg {
  display: block;
  width: 100%;
  height: auto;
}

.audit-list {
  display: grid;
  gap: 9px;
}

.audit-item {
  padding: 12px 14px;
  line-height: 1.5;
}

.empty-note {
  margin: 0;
  padding: 18px;
  color: #d9e4df;
}

.fade {
  opacity: 0;
  transform: translateY(10px);
  animation: fadeIn 0.55s ease forwards;
  animation-delay: calc(var(--delay, 1) * 70ms);
}

.fade[data-delay="1"] { --delay: 1; }
.fade[data-delay="2"] { --delay: 2; }
.fade[data-delay="3"] { --delay: 3; }

@keyframes fadeIn {
  to {
    opacity: 1;
    transform: none;
  }
}

@media (max-width: 1080px) {
  .hero,
  .investigation-layout,
  .policy-grid {
    grid-template-columns: 1fr;
  }

  .case-detail {
    min-height: 0;
  }
}

@media (max-width: 760px) {
  .shell {
    width: min(100% - 24px, 1360px);
    padding-top: 16px;
  }

  .topbar,
  .section-head {
    align-items: stretch;
    flex-direction: column;
  }

  .hero-panel,
  .stream-panel,
  .investigation-panel,
  .case-detail {
    padding: 14px;
  }

  .hero h1 {
    font-size: clamp(2.5rem, 18vw, 4.2rem);
  }

  .hero-grid,
  .case-metrics,
  .case-process,
  .threshold-list {
    grid-template-columns: 1fr;
  }

  .level-row {
    grid-template-columns: 76px minmax(0, 1fr) 36px;
  }
}

@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.001ms !important;
    animation-iteration-count: 1 !important;
    scroll-behavior: auto !important;
  }
}
"""


REFRESH_STYLE = """
"""


HTML_SCRIPT = """
const payload = JSON.parse(document.getElementById('dashboard-data').textContent);

const state = {
  selectedCase: payload.investigation?.cases?.[0]?.caseId || null,
  lastRefreshAt: new Date(),
};

const levelMeta = {
  critical: { label: 'critical', color: '#b8322a', text: '高危冻结' },
  high: { label: 'high', color: '#b36a13', text: '人工复核' },
  medium: { label: 'medium', color: '#256b8f', text: '二次验证' },
  low: { label: 'low', color: '#1f7a62', text: '自动放行' },
};

const formatNumber = (value) => new Intl.NumberFormat('zh-CN').format(Number(value || 0));
const formatScore = (value) => Number.isFinite(Number(value)) ? Number(value).toFixed(4) : '--';
const formatAmount = (value) => Number.isFinite(Number(value)) ? Number(value).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '--';

const getSummary = () => payload.investigation?.summary || {};
const getCases = () => payload.investigation?.cases || [];

const countByLevel = (summary) => ({
  critical: summary.criticalCount || 0,
  high: summary.highCount || 0,
  medium: summary.mediumCount || 0,
  low: summary.lowCount || 0,
});

const createMetricCards = (items) => items.map((item) => `
  <div class="mini-stat">
    <span>${item.label}</span>
    <strong>${item.value}</strong>
  </div>
`).join('');

const renderHero = () => {
  const summary = getSummary();
  const criticalHighCount = (summary.criticalCount || 0) + (summary.highCount || 0);
  const statValues = {
    '{caseCount}': formatNumber(summary.caseCount || 0),
    '{criticalHighCount}': formatNumber(criticalHighCount),
  };

  document.getElementById('hero-eyebrow').textContent = payload.meta.eyebrow;
  document.getElementById('hero-title').textContent = payload.meta.title;
  document.getElementById('hero-intro').textContent = payload.meta.intro;
  document.getElementById('generated-at').textContent = payload.meta.generatedAt;
  document.getElementById('stream-status').textContent = payload.meta.mode;
  document.getElementById('stack-name').textContent = payload.meta.stack;
  document.getElementById('hero-stats').innerHTML = payload.heroStats.map((item) => {
    const value = statValues[item.value] || item.value;
    return `
      <div class="hero-stat">
        <span class="label">${item.label}</span>
        <strong>${value}</strong>
        <small>${item.note}</small>
      </div>
    `;
  }).join('');
  document.getElementById('signal-strip').innerHTML = payload.signals.map((item) => `<span class="signal-chip">${item}</span>`).join('');
};

const renderLevelBars = () => {
  const counts = countByLevel(getSummary());
  const maxCount = Math.max(1, ...Object.values(counts));
  document.getElementById('level-bars').innerHTML = Object.entries(levelMeta).map(([level, meta]) => `
    <div class="level-row">
      <span>${meta.label}</span>
      <div class="level-track" style="--bar-color:${meta.color}; --fill:${counts[level] / maxCount}">
        <span></span>
      </div>
      <strong>${formatNumber(counts[level])}</strong>
    </div>
  `).join('');
};

const renderLatest = () => {
  const cases = getCases();
  const latest = cases[0];
  if (!latest) {
    document.getElementById('latest-score').textContent = '--';
    document.getElementById('latest-event').textContent = '等待风险事件';
    return;
  }
  document.getElementById('latest-score').textContent = formatScore(latest.riskScore);
  document.getElementById('latest-event').textContent = `事件 ${latest.eventId} / ${latest.riskLevel} / ${latest.action}`;
};

const renderPolicy = () => {
  const policy = payload.policy;
  const counts = countByLevel(getSummary());
  document.getElementById('policy-grid').innerHTML = `
    <article class="policy-card">
      <span>在线模型</span>
      <strong>${policy.model.version}</strong>
      <span style="margin-top:12px;">训练数据与基准</span>
      <strong>${policy.model.dataset} / AUC ${formatScore(policy.model.auc)}</strong>
    </article>
    <article class="policy-card">
      <span>风险等级策略</span>
      <div class="threshold-list">
        ${policy.thresholds.map((item) => `
          <div class="threshold-item">
            <span>${levelMeta[item.level]?.text || item.level}</span>
            <strong>${Number(item.threshold).toFixed(2)}</strong>
            <span>${item.action}</span>
            <span>命中 ${formatNumber(counts[item.level] ?? item.hitCount)}</span>
          </div>
        `).join('')}
      </div>
    </article>
    <article class="policy-card">
      <span>识别输出</span>
      <strong>${policy.batch.output}</strong>
      <span style="margin-top:12px;">审计摘要</span>
      <strong>${policy.batch.audit}</strong>
    </article>
  `;
};

const caseLevelColor = (level) => levelMeta[level]?.color || '#69736f';

const renderTraceCanvas = (caseItem) => {
  const trace = caseItem.trace || {};
  const width = 760;
  const height = 280;
  const cx = 188;
  const cy = 140;
  const groups = [
    { label: '欺诈邻居', count: trace.fraudNeighborCount || 0, color: '#f05a4f' },
    { label: '正常邻居', count: trace.normalNeighborCount || 0, color: '#4fb28f' },
    { label: '背景节点', count: trace.backgroundNeighborCount || 0, color: '#d5972a' },
  ].filter((item) => item.count > 0);
  const nodes = [];
  groups.forEach((group) => {
    const visible = Math.min(group.count, 8);
    for (let index = 0; index < visible; index += 1) nodes.push(group);
  });
  const nodeMarkup = nodes.map((node, index) => {
    const angle = -Math.PI / 2 + (Math.PI * 2 * index) / Math.max(1, nodes.length);
    const x = cx + Math.cos(angle) * 118;
    const y = cy + Math.sin(angle) * 88;
    return `
      <line x1="${cx}" y1="${cy}" x2="${x}" y2="${y}" stroke="rgba(255,253,246,0.22)" stroke-width="1.8" />
      <circle cx="${x}" cy="${y}" r="9" fill="${node.color}" />
    `;
  }).join('');
  const legend = groups.map((item, index) => `
    <g transform="translate(430 ${78 + index * 32})">
      <circle cx="0" cy="0" r="7" fill="${item.color}" />
      <text x="16" y="5" fill="#f3eee2" font-size="14">${item.label} ${item.count}</text>
    </g>
  `).join('');

  return `
    <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="风险事件一跳邻域摘要">
      <rect x="12" y="12" width="${width - 24}" height="${height - 24}" rx="16" fill="rgba(255,253,246,0.035)" stroke="rgba(255,253,246,0.12)" />
      ${nodeMarkup}
      <circle cx="${cx}" cy="${cy}" r="24" fill="${caseLevelColor(caseItem.riskLevel)}" />
      <text x="${cx}" y="${cy + 48}" text-anchor="middle" fill="#f3eee2" font-size="13">focus ${caseItem.focusNode}</text>
      <text x="430" y="42" fill="#fffdf6" font-size="16" font-weight="700">动态异常摘要</text>
      ${legend}
      <text x="430" y="196" fill="#cfd9d4" font-size="13">关联边 ${trace.incidentEdgeCount || 0} / 主导交易类型 ${trace.dominantEdgeType || caseItem.edgeType || '-'}</text>
      <text x="430" y="222" fill="#cfd9d4" font-size="13">时间跨度 ${trace.timeSpan || 0} / 邻居覆盖 ${trace.neighborCount || 0} 个节点</text>
      <text x="430" y="248" fill="#cfd9d4" font-size="13">主导类型占比 ${((trace.dominantEdgeTypeShare || 0) * 100).toFixed(1)}%</text>
    </svg>
  `;
};

const renderCaseDetail = () => {
  const cases = getCases();
  const caseItem = cases.find((item) => item.caseId === state.selectedCase) || cases[0];
  if (!caseItem) {
    document.getElementById('case-kicker').textContent = '暂无风险事件';
    document.getElementById('case-title').textContent = '请先运行交易流回放或导入风险事件';
    document.getElementById('case-status').textContent = '未生成';
    document.getElementById('case-metrics').innerHTML = '';
    document.getElementById('case-process').innerHTML = '';
    document.getElementById('trace-canvas').innerHTML = '<p class="empty-note">缺少交易流风险事件。</p>';
    document.getElementById('audit-list').innerHTML = '';
    return;
  }

  state.selectedCase = caseItem.caseId;
  document.getElementById('case-kicker').textContent = `事件 ${caseItem.eventId} / ${caseItem.channel}`;
  document.getElementById('case-title').textContent = `${caseItem.caseId}  焦点节点 ${caseItem.focusNode}`;
  document.getElementById('case-status').textContent = caseItem.status;
  document.getElementById('case-metrics').innerHTML = createMetricCards([
    { label: '风险分', value: formatScore(caseItem.riskScore) },
    { label: '风险等级', value: caseItem.riskLevel },
    { label: '欺诈判定', value: caseItem.riskLevel === 'low' ? '放行' : '疑似欺诈' },
    { label: '交易金额', value: formatAmount(caseItem.amount) },
  ]);
  document.getElementById('case-process').innerHTML = `
    <div class="case-process-item">
      <span>处置动作</span>
      ${caseItem.action}
    </div>
    <div class="case-process-item">
      <span>复核结论</span>
      ${caseItem.review}
    </div>
    <div class="case-process-item">
      <span>行为解释</span>
      ${caseItem.explanation}
    </div>
  `;
  document.getElementById('trace-canvas').innerHTML = renderTraceCanvas(caseItem);
  document.getElementById('audit-list').innerHTML = (caseItem.audit || []).map((item, index) => `
    <div class="audit-item">
      <span>输出记录 ${String(index + 1).padStart(2, '0')}</span>
      ${item}
    </div>
  `).join('');
  document.querySelectorAll('.case-button').forEach((button) => {
    button.classList.toggle('active', button.dataset.caseId === caseItem.caseId);
  });
};

const renderInvestigation = () => {
  const cases = getCases();
  document.getElementById('case-list').innerHTML = cases.map((item) => `
    <button class="case-button ${item.caseId === state.selectedCase ? 'active' : ''}" type="button" data-case-id="${item.caseId}">
      <span>${item.status}</span>
      <strong><span>${item.caseId}</span><span style="color:${caseLevelColor(item.riskLevel)}">${item.riskLevel}</span></strong>
      <span>score ${formatScore(item.riskScore)} / ${item.action}</span>
      <span>${item.srcNode} -> ${item.dstNode} / ${item.channel}</span>
    </button>
  `).join('');
  document.querySelectorAll('.case-button').forEach((button) => {
    button.addEventListener('click', () => {
      state.selectedCase = button.dataset.caseId;
      renderCaseDetail();
    });
  });
  renderCaseDetail();
};

const renderRefreshNote = () => {
  document.getElementById('refresh-note').textContent = `更新 ${state.lastRefreshAt.toLocaleTimeString('zh-CN', { hour12: false })}`;
};

const renderAll = () => {
  renderHero();
  renderLatest();
  renderLevelBars();
  renderPolicy();
  renderInvestigation();
  renderRefreshNote();
};

const refreshLiveRiskEvents = async () => {
  try {
    const response = await fetch('/api/risk-events?limit=12', { cache: 'no-store' });
    if (!response.ok) return;
    const nextInvestigation = await response.json();
    const previousFirstCase = payload.investigation?.cases?.[0]?.caseId || null;
    const nextFirstCase = nextInvestigation?.cases?.[0]?.caseId || null;
    payload.investigation = nextInvestigation;
    if (!state.selectedCase || state.selectedCase === previousFirstCase) {
      state.selectedCase = nextFirstCase;
    }
    state.lastRefreshAt = new Date();
    renderAll();
  } catch (error) {
    renderRefreshNote();
  }
};

const renderRiskScene = () => {
  const canvas = document.getElementById('risk-3d');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const nodes = Array.from({ length: 46 }, (_, index) => ({
    angle: (Math.PI * 2 * index) / 46,
    radius: 74 + (index % 4) * 26,
    risk: index % 9 === 0 || index % 13 === 0,
  }));
  const links = nodes.map((_, index) => [index, (index + 5) % nodes.length]);

  const draw = (time) => {
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
    const cx = rect.width * 0.5;
    const cy = rect.height * 0.52;
    const t = time * 0.00028;
    const points = nodes.map((node, index) => {
      const pulse = Math.sin(t * 5 + index) * 8;
      return {
        x: cx + Math.cos(node.angle + t) * (node.radius + pulse),
        y: cy + Math.sin(node.angle + t * 0.8) * (node.radius * 0.62 + pulse),
        risk: node.risk,
      };
    });

    const gradient = ctx.createRadialGradient(cx, cy, 0, cx, cy, Math.min(rect.width, rect.height) * 0.65);
    gradient.addColorStop(0, 'rgba(79,178,143,0.24)');
    gradient.addColorStop(0.55, 'rgba(37,107,143,0.12)');
    gradient.addColorStop(1, 'rgba(24,33,31,0)');
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, rect.width, rect.height);

    links.forEach(([source, target]) => {
      const from = points[source];
      const to = points[target];
      ctx.strokeStyle = from.risk || to.risk ? 'rgba(240,90,79,0.32)' : 'rgba(255,253,246,0.16)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(from.x, from.y);
      ctx.lineTo(to.x, to.y);
      ctx.stroke();
    });

    points.forEach((point) => {
      ctx.beginPath();
      ctx.fillStyle = point.risk ? 'rgba(240,90,79,0.9)' : 'rgba(79,178,143,0.82)';
      ctx.arc(point.x, point.y, point.risk ? 4.6 : 3.1, 0, Math.PI * 2);
      ctx.fill();
    });

    requestAnimationFrame(draw);
  };

  requestAnimationFrame(draw);
};

renderAll();
renderRiskScene();
refreshLiveRiskEvents();
setInterval(refreshLiveRiskEvents, 2000);
"""
