from __future__ import annotations


HTML_STYLE = """
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&family=IBM+Plex+Sans:wght@400;500;600&family=JetBrains+Mono:wght@400;600&display=swap');

:root {
  --bg: #07131b;
  --panel: rgba(10, 29, 41, 0.82);
  --panel-strong: rgba(12, 35, 51, 0.94);
  --panel-soft: rgba(18, 46, 63, 0.72);
  --line: rgba(151, 186, 194, 0.18);
  --text: #edf3ef;
  --muted: #8ea4a9;
  --accent: #f2b35d;
  --accent-2: #8ee0c8;
  --danger: #ff7c6b;
  --context: #6f8f97;
  --shadow: 0 28px 80px rgba(0, 0, 0, 0.28);
  --radius-xl: 28px;
  --radius-lg: 22px;
  --radius-md: 16px;
  --radius-sm: 12px;
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
  color: var(--text);
  background:
    radial-gradient(circle at 12% 18%, rgba(242, 179, 93, 0.18), transparent 28%),
    radial-gradient(circle at 88% 14%, rgba(142, 224, 200, 0.16), transparent 24%),
    radial-gradient(circle at 52% 82%, rgba(46, 83, 102, 0.26), transparent 32%),
    linear-gradient(180deg, #08131b 0%, #07131b 46%, #091b24 100%);
  font-family: 'IBM Plex Sans', 'Segoe UI', sans-serif;
}

body::before {
  content: "";
  position: fixed;
  inset: 0;
  pointer-events: none;
  background:
    linear-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.025) 1px, transparent 1px);
  background-size: 48px 48px;
  mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.6), transparent 85%);
}

.skip-link {
  position: absolute;
  left: 12px;
  top: -48px;
  z-index: 100;
  padding: 10px 14px;
  color: #061217;
  background: var(--accent-2);
  border-radius: 999px;
  transition: top 0.2s ease;
}

.skip-link:focus {
  top: 12px;
}

.shell {
  width: min(1280px, calc(100vw - 40px));
  margin: 0 auto;
  padding: 28px 0 56px;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 28px;
  color: var(--muted);
}

.brand {
  display: flex;
  align-items: center;
  gap: 14px;
}

.brand-mark {
  width: 46px;
  height: 46px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  font-family: 'JetBrains Mono', monospace;
  font-weight: 600;
  letter-spacing: 0.08em;
  background: linear-gradient(135deg, rgba(242, 179, 93, 0.34), rgba(142, 224, 200, 0.18));
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.08);
}

.brand-copy strong,
.brand-copy span {
  display: block;
}

.brand-copy strong {
  color: var(--text);
  font-size: 0.98rem;
}

.brand-copy span {
  font-size: 0.8rem;
}

.topbar-meta {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.pill {
  padding: 9px 14px;
  border-radius: 999px;
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.04);
  font-size: 0.82rem;
}

.hero {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(360px, 0.9fr);
  gap: 22px;
  margin-bottom: 22px;
}

.hero-panel,
.panel {
  position: relative;
  overflow: hidden;
  border-radius: var(--radius-xl);
  border: 1px solid var(--line);
  background: linear-gradient(180deg, rgba(15, 37, 52, 0.92), rgba(8, 24, 34, 0.92));
  box-shadow: var(--shadow);
}

.hero-panel {
  min-height: 520px;
  padding: 34px 34px 30px;
}

.hero-panel::before,
.panel::before {
  content: "";
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at top right, rgba(242, 179, 93, 0.08), transparent 30%);
  pointer-events: none;
}

.eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 9px 14px;
  border-radius: 999px;
  color: var(--accent-2);
  background: rgba(142, 224, 200, 0.08);
  border: 1px solid rgba(142, 224, 200, 0.18);
  font-size: 0.82rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.hero h1 {
  max-width: 12ch;
  margin: 20px 0 16px;
  font-family: 'Fraunces', Georgia, serif;
  font-size: clamp(2.8rem, 5vw, 5rem);
  line-height: 0.95;
  letter-spacing: -0.04em;
}

.hero-intro {
  max-width: 62ch;
  font-size: 1rem;
  line-height: 1.75;
  color: #d7e2de;
}

.hero-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin-top: 26px;
}

.hero-stat {
  padding: 16px 18px;
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.hero-stat .label {
  display: block;
  font-size: 0.8rem;
  color: var(--muted);
  margin-bottom: 8px;
}

.hero-stat strong {
  font-size: 1.34rem;
  line-height: 1.1;
}

.hero-stat small {
  display: block;
  margin-top: 10px;
  color: var(--muted);
  line-height: 1.45;
}

.hero-side {
  display: grid;
  grid-template-rows: minmax(0, 1fr) auto;
  gap: 22px;
}

.score-orbit {
  display: grid;
  place-items: center;
  min-height: 332px;
  padding: 26px;
}

.score-ring {
  position: relative;
  width: min(100%, 320px);
  aspect-ratio: 1;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background:
    radial-gradient(circle at center, rgba(7, 19, 27, 0.96) 0 54%, transparent 54% 100%),
    conic-gradient(from -90deg, var(--accent) calc(var(--score) * 1%), rgba(255, 255, 255, 0.08) 0);
  box-shadow:
    inset 0 0 0 18px rgba(255, 255, 255, 0.03),
    0 24px 80px rgba(0, 0, 0, 0.34);
}

.score-ring::before {
  content: "";
  position: absolute;
  inset: 18px;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.score-copy {
  position: relative;
  text-align: center;
}

.score-copy .meta {
  display: block;
  margin-bottom: 10px;
  color: var(--muted);
  letter-spacing: 0.14em;
  text-transform: uppercase;
  font-size: 0.74rem;
}

.score-copy strong {
  display: block;
  font-family: 'Fraunces', Georgia, serif;
  font-size: clamp(2.4rem, 4vw, 3.9rem);
  line-height: 1;
  letter-spacing: -0.04em;
}

.score-copy small {
  display: block;
  margin-top: 12px;
  color: #d2d8d2;
}

.hero-notes {
  padding: 22px 24px 24px;
}

.hero-notes h2,
.section-head h2,
.detail-panel h3,
.graph-copy h3,
.flow-panel h3,
.board h3,
.sources h3 {
  margin: 0 0 10px;
  font-size: 1rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.hero-notes ul,
.detail-top-features,
.sources ul {
  margin: 0;
  padding: 0;
  list-style: none;
}

.hero-notes li,
.detail-top-features li,
.sources li {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  color: #d2ddda;
  line-height: 1.6;
}

.hero-notes li + li,
.detail-top-features li + li,
.sources li + li {
  margin-top: 12px;
}

.hero-notes li::before,
.detail-top-features li::before,
.sources li::before {
  content: "";
  flex: 0 0 8px;
  width: 8px;
  height: 8px;
  margin-top: 9px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--accent), var(--accent-2));
}

.section {
  margin-top: 22px;
}

.section-head {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  align-items: end;
  margin-bottom: 14px;
}

.section-head p {
  max-width: 66ch;
  margin: 0;
  color: var(--muted);
  line-height: 1.6;
}

.dataset-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 14px;
}

.dataset-card {
  position: relative;
  padding: 18px 18px 16px;
  border-radius: var(--radius-lg);
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.06), rgba(255, 255, 255, 0.03));
  color: inherit;
  text-align: left;
  cursor: pointer;
  transition: transform 0.22s ease, border-color 0.22s ease, background 0.22s ease;
}

.dataset-card:hover,
.dataset-card:focus-visible {
  transform: translateY(-3px);
  border-color: rgba(242, 179, 93, 0.42);
  outline: none;
}

.dataset-card.active {
  background: linear-gradient(180deg, rgba(242, 179, 93, 0.12), rgba(142, 224, 200, 0.06));
  border-color: rgba(242, 179, 93, 0.5);
}

.dataset-card .tagline,
.dataset-card .mode,
.dataset-card .trust {
  display: block;
}

.dataset-card .tagline {
  margin-bottom: 12px;
  color: var(--accent-2);
  font-size: 0.76rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.dataset-card h3 {
  margin: 0 0 12px;
  font-size: 1.05rem;
}

.dataset-card .mode,
.dataset-card .trust {
  color: var(--muted);
  font-size: 0.84rem;
  line-height: 1.55;
}

.dataset-card .auc {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin: 18px 0 10px;
}

.dataset-card .auc strong {
  font-family: 'Fraunces', Georgia, serif;
  font-size: 2rem;
  letter-spacing: -0.04em;
}

.track {
  position: relative;
  height: 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  overflow: hidden;
}

.track span {
  position: absolute;
  inset: 0 auto 0 0;
  width: calc(var(--fill) * 100%);
  border-radius: inherit;
  background: linear-gradient(90deg, var(--accent), var(--accent-2));
}

.detail-wrap {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(300px, 0.9fr);
  gap: 16px;
  margin-top: 16px;
}

.profile-panel {
  margin-top: 16px;
  padding: 24px;
  border-radius: var(--radius-xl);
  border: 1px solid var(--line);
  background: var(--panel);
  box-shadow: var(--shadow);
}

.profile-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.profile-block {
  padding: 18px;
  border-radius: var(--radius-lg);
  background: rgba(255, 255, 255, 0.045);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.profile-block h3 {
  margin: 0 0 16px;
  font-size: 0.96rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.dist-row + .dist-row {
  margin-top: 13px;
}

.dist-label {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 7px;
  color: #d8e2df;
}

.dist-label span {
  color: var(--muted);
  font-size: 0.86rem;
}

.dist-label strong {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.86rem;
}

.dist-track {
  position: relative;
  height: 9px;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
}

.dist-track span {
  display: block;
  height: 100%;
  border-radius: inherit;
}

.schema-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.schema-chip {
  display: inline-flex;
  flex-direction: column;
  gap: 5px;
  min-width: 126px;
  padding: 11px 12px;
  border-radius: var(--radius-md);
  background: rgba(0, 0, 0, 0.16);
  border: 1px solid rgba(255, 255, 255, 0.07);
}

.schema-chip strong {
  font-size: 0.86rem;
  color: #edf3ef;
}

.schema-chip small {
  color: var(--muted);
  line-height: 1.35;
}

.sample-table-wrap {
  overflow-x: auto;
  border-radius: var(--radius-md);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.sample-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 620px;
  font-family: 'JetBrains Mono', Consolas, monospace;
  font-size: 0.78rem;
}

.sample-table th,
.sample-table td {
  padding: 10px 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.07);
  text-align: left;
  white-space: nowrap;
}

.sample-table th {
  color: var(--accent-2);
  background: rgba(142, 224, 200, 0.06);
  font-weight: 600;
}

.sample-table td {
  color: #d7e2de;
}

.empty-note {
  margin: 0;
  color: var(--muted);
  line-height: 1.6;
}

.detail-panel,
.detail-side,
.graph-panel,
.flow-panel,
.board,
.sources {
  padding: 24px;
}

.detail-panel,
.detail-side,
.graph-panel,
.flow-panel,
.board,
.sources {
  border-radius: var(--radius-xl);
  border: 1px solid var(--line);
  background: var(--panel);
  box-shadow: var(--shadow);
}

.detail-kicker {
  color: var(--accent-2);
  font-size: 0.82rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.detail-title-row {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 18px;
  margin-top: 8px;
}

.detail-title-row h3 {
  margin-bottom: 0;
  font-size: 1.7rem;
  font-family: 'Fraunces', Georgia, serif;
  letter-spacing: -0.03em;
}

.detail-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.badge {
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.09);
  color: #d1ddda;
  font-size: 0.8rem;
}

.detail-summary {
  margin: 16px 0 0;
  color: #d6dfdc;
  line-height: 1.7;
}

.detail-metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-top: 20px;
}

.mini-stat {
  padding: 16px 14px;
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.mini-stat span {
  display: block;
  color: var(--muted);
  font-size: 0.76rem;
  margin-bottom: 8px;
}

.mini-stat strong {
  font-size: 1.08rem;
  line-height: 1.3;
}

.detail-annotations {
  margin-top: 20px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.annotation {
  padding: 16px;
  border-radius: var(--radius-md);
  background: rgba(0, 0, 0, 0.18);
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.annotation span {
  display: block;
  color: var(--muted);
  font-size: 0.78rem;
  margin-bottom: 8px;
}

.annotation strong {
  display: block;
  font-size: 0.98rem;
  line-height: 1.55;
}

.detail-side h3 {
  margin-bottom: 18px;
}

.side-block + .side-block {
  margin-top: 20px;
}

.side-block span {
  display: block;
  margin-bottom: 10px;
  color: var(--muted);
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.side-block p {
  margin: 0;
  color: #d4ddda;
  line-height: 1.7;
}

.graph-layout {
  display: grid;
  grid-template-columns: minmax(340px, 0.9fr) minmax(0, 1.1fr);
  gap: 16px;
}

.graph-stage {
  padding: 12px;
  border-radius: var(--radius-lg);
  background: radial-gradient(circle at center, rgba(142, 224, 200, 0.05), rgba(255, 255, 255, 0.01));
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.graph-stage svg {
  width: 100%;
  height: auto;
  display: block;
}

.graph-copy p {
  margin: 0;
  color: #d4ddda;
  line-height: 1.7;
}

.graph-facts {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin: 18px 0;
}

.graph-fact {
  padding: 14px;
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.graph-fact span {
  display: block;
  color: var(--muted);
  font-size: 0.76rem;
  margin-bottom: 8px;
}

.graph-fact strong {
  font-size: 1rem;
}

.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 16px;
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  padding: 8px 11px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.05);
  font-size: 0.82rem;
}

.legend-swatch {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.flow-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.flow-step {
  padding: 18px;
  border-radius: var(--radius-lg);
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.flow-step .step-id {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border-radius: 50%;
  margin-bottom: 14px;
  background: linear-gradient(135deg, rgba(242, 179, 93, 0.18), rgba(142, 224, 200, 0.14));
  border: 1px solid rgba(242, 179, 93, 0.25);
  color: var(--accent);
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.84rem;
}

.flow-step h4 {
  margin: 0 0 10px;
  font-size: 1rem;
}

.flow-step p {
  margin: 0;
  color: #d4ddda;
  line-height: 1.66;
}

.board-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.story-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.scenario-panel,
.investigation-panel,
.reference-panel {
  padding: 24px;
  border-radius: var(--radius-xl);
  border: 1px solid var(--line);
  background: var(--panel);
  box-shadow: var(--shadow);
}

.reference-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.reference-card {
  display: grid;
  gap: 12px;
  min-height: 260px;
  padding: 18px;
  border-radius: var(--radius-lg);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.055), rgba(255, 255, 255, 0.03));
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.reference-card h4 {
  margin: 0;
  font-size: 1.02rem;
}

.reference-card .reference-block {
  padding: 12px;
  border-radius: var(--radius-md);
  background: rgba(0, 0, 0, 0.13);
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.reference-card .reference-block span {
  display: block;
  margin-bottom: 7px;
  color: var(--accent);
  font-size: 0.76rem;
  font-weight: 700;
}

.reference-card .reference-block p {
  margin: 0;
  color: #d2dcda;
  line-height: 1.58;
}

.scenario-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.scenario-card {
  padding: 18px;
  border-radius: var(--radius-lg);
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.scenario-card header,
.case-detail-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 14px;
}

.scenario-card h4,
.case-detail h3 {
  margin: 0;
}

.scenario-card p {
  margin: 0;
  color: #d2dcda;
  line-height: 1.65;
}

.scenario-card p + p {
  margin-top: 12px;
}

.scenario-action {
  width: 100%;
  margin: 14px 0 0;
  padding: 10px 12px;
  border: 1px solid rgba(215, 255, 114, 0.28);
  border-radius: var(--radius-md);
  color: #061217;
  background: var(--accent);
  font-weight: 700;
  cursor: pointer;
}

.scenario-result {
  display: grid;
  gap: 8px;
  margin-top: 12px;
  padding: 12px;
  border-radius: var(--radius-md);
  background: rgba(215, 255, 114, 0.08);
  border: 1px solid rgba(215, 255, 114, 0.18);
}

.scenario-result span {
  display: block;
  color: var(--muted);
  font-size: 0.76rem;
}

.scenario-result strong {
  color: #edf3ef;
  font-family: 'JetBrains Mono', Consolas, monospace;
}

.scenario-flow {
  min-height: 82px;
  margin: 16px 0;
  display: grid;
  place-items: center;
  border-radius: var(--radius-md);
  background: rgba(0, 0, 0, 0.18);
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.scenario-flow svg {
  width: 100%;
  height: 82px;
  display: block;
}

.policy-grid {
  display: grid;
  grid-template-columns: 1.1fr 1.4fr 1fr;
  gap: 12px;
  margin-bottom: 16px;
}

.policy-card {
  padding: 16px;
  border-radius: var(--radius-lg);
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.policy-card span,
.case-button span,
.audit-item span {
  display: block;
  color: var(--muted);
  font-size: 0.76rem;
  margin-bottom: 7px;
}

.policy-card strong {
  display: block;
  color: #edf3ef;
  line-height: 1.35;
}

.threshold-list {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.threshold-item {
  padding: 10px;
  border-radius: var(--radius-md);
  background: rgba(0, 0, 0, 0.14);
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.investigation-layout {
  display: grid;
  grid-template-columns: minmax(280px, 0.42fr) minmax(0, 1fr);
  gap: 16px;
}

.case-list {
  display: grid;
  gap: 10px;
  align-content: start;
}

.case-button {
  width: 100%;
  padding: 14px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.045);
  color: inherit;
  text-align: left;
  cursor: pointer;
}

.case-button.active,
.case-button:hover,
.case-button:focus-visible {
  outline: none;
  border-color: rgba(215, 255, 114, 0.42);
  background: rgba(215, 255, 114, 0.08);
}

.case-button strong {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}

.case-detail {
  min-width: 0;
  padding: 18px;
  border-radius: var(--radius-lg);
  background: rgba(0, 0, 0, 0.14);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.case-metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin: 14px 0;
}

.case-process {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 14px;
}

.case-process-item {
  padding: 12px;
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.045);
  border: 1px solid rgba(255, 255, 255, 0.06);
  color: #d2dcda;
  line-height: 1.5;
}

.case-process-item span {
  display: block;
  margin-bottom: 7px;
  color: var(--muted);
  font-size: 0.76rem;
}

.trace-canvas {
  min-height: 280px;
  border-radius: var(--radius-md);
  background: radial-gradient(circle at center, rgba(77, 214, 255, 0.08), rgba(0, 0, 0, 0.18));
  border: 1px solid rgba(255, 255, 255, 0.08);
  overflow: hidden;
}

.trace-canvas svg {
  width: 100%;
  height: 280px;
  display: block;
}

.audit-list {
  display: grid;
  gap: 10px;
  margin-top: 14px;
}

.audit-item {
  padding: 12px;
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.045);
  border: 1px solid rgba(255, 255, 255, 0.06);
  color: #d2dcda;
  line-height: 1.55;
}

.status-card {
  padding: 18px;
  border-radius: var(--radius-lg);
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.status-card header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 14px;
}

.status-card h4 {
  margin: 0;
  font-size: 1rem;
}

.status-chip {
  padding: 7px 10px;
  border-radius: 999px;
  font-size: 0.76rem;
  background: rgba(255, 255, 255, 0.06);
  color: var(--muted);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.status-card p {
  margin: 0;
  color: #d2dcda;
  line-height: 1.7;
}

.caveat-list {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.caveat {
  padding: 16px;
  border-radius: var(--radius-md);
  background: linear-gradient(180deg, rgba(255, 124, 107, 0.08), rgba(255, 255, 255, 0.03));
  border: 1px solid rgba(255, 124, 107, 0.16);
  color: #eadad7;
  line-height: 1.64;
}

.caveat strong {
  display: block;
  margin-bottom: 8px;
  color: #ffe6d9;
}

.sources p,
.sources footer {
  color: var(--muted);
  line-height: 1.66;
}

.sources footer {
  margin-top: 18px;
  font-size: 0.84rem;
}

.fade {
  opacity: 0;
  transform: translateY(16px);
  animation: rise 0.72s ease forwards;
}

.fade[data-delay="1"] { animation-delay: 0.05s; }
.fade[data-delay="2"] { animation-delay: 0.12s; }
.fade[data-delay="3"] { animation-delay: 0.18s; }
.fade[data-delay="4"] { animation-delay: 0.24s; }
.fade[data-delay="5"] { animation-delay: 0.3s; }

@keyframes rise {
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (prefers-reduced-motion: reduce) {
  html {
    scroll-behavior: auto;
  }

  .fade,
  .dataset-card {
    animation: none !important;
    transition: none !important;
    opacity: 1;
    transform: none;
  }
}

@media (max-width: 1120px) {
  .dataset-grid,
  .caveat-list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .hero,
  .detail-wrap,
  .profile-grid,
  .graph-layout,
  .flow-grid,
  .board-grid,
  .story-grid,
  .reference-grid,
  .scenario-grid,
  .policy-grid,
  .investigation-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 860px) {
  .shell {
    width: min(100vw - 24px, 1280px);
    padding-top: 18px;
  }

  .topbar,
  .section-head,
  .detail-title-row {
    display: block;
  }

  .topbar-meta,
  .detail-badges {
    margin-top: 12px;
    justify-content: flex-start;
  }

  .hero-panel,
  .detail-panel,
  .detail-side,
  .profile-block,
  .graph-panel,
  .flow-panel,
  .board,
  .reference-panel,
  .scenario-panel,
  .investigation-panel,
  .sources {
    padding: 20px;
  }

  .hero-grid,
  .detail-metrics,
  .detail-annotations,
  .graph-facts,
  .dataset-grid,
  .caveat-list,
  .threshold-list,
  .case-process,
  .case-metrics {
    grid-template-columns: 1fr;
  }

  .graph-facts {
    width: 100%;
  }
}
"""


REFRESH_STYLE = """
:root {
  --bg: #05080d;
  --panel: rgba(8, 15, 24, 0.78);
  --panel-strong: rgba(10, 20, 32, 0.94);
  --panel-soft: rgba(18, 32, 47, 0.72);
  --line: rgba(156, 202, 213, 0.18);
  --text: #f4f7f5;
  --muted: #9aaab0;
  --accent: #d7ff72;
  --accent-2: #4dd6ff;
  --danger: #ff6b7a;
  --context: #7b8994;
  --shadow: 0 34px 110px rgba(0, 0, 0, 0.42);
  --radius-xl: 18px;
  --radius-lg: 14px;
  --radius-md: 10px;
  --radius-sm: 8px;
}

body {
  background:
    linear-gradient(110deg, rgba(215, 255, 114, 0.08), transparent 28%),
    linear-gradient(260deg, rgba(77, 214, 255, 0.12), transparent 34%),
    radial-gradient(circle at 50% -10%, rgba(255, 255, 255, 0.08), transparent 28%),
    #05080d;
}

body::before {
  background:
    linear-gradient(rgba(255, 255, 255, 0.028) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.022) 1px, transparent 1px);
  background-size: 36px 36px;
}

.shell {
  width: min(1420px, calc(100vw - 48px));
}

.brand-mark {
  border-radius: 10px;
  background: linear-gradient(135deg, rgba(215, 255, 114, 0.26), rgba(77, 214, 255, 0.14));
}

.pill,
.badge,
.status-chip {
  border-radius: 999px;
}

.hero {
  grid-template-columns: minmax(0, 0.95fr) minmax(440px, 1.05fr);
}

.hero-panel,
.panel,
.detail-panel,
.detail-side,
.graph-panel,
.flow-panel,
.board,
.sources,
.profile-panel {
  background:
    linear-gradient(180deg, rgba(16, 29, 43, 0.88), rgba(7, 13, 22, 0.9)),
    radial-gradient(circle at 18% 0%, rgba(77, 214, 255, 0.08), transparent 38%);
  border-color: rgba(160, 205, 215, 0.16);
  box-shadow: var(--shadow);
}

.hero-panel {
  min-height: 560px;
  padding: 42px;
}

.eyebrow {
  color: #0b1014;
  background: var(--accent);
  border-color: transparent;
  font-weight: 700;
}

.hero h1 {
  max-width: 10ch;
  font-family: 'IBM Plex Sans', 'Segoe UI', sans-serif;
  font-weight: 600;
  letter-spacing: 0;
  line-height: 1.02;
}

.hero-intro {
  max-width: 60ch;
  color: #c8d4d6;
}

.hero-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.hero-stat,
.mini-stat,
.annotation,
.profile-block,
.flow-step,
.status-card,
.caveat,
.graph-stage {
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.045);
  border-color: rgba(255, 255, 255, 0.08);
}

.hero-stat strong,
.mini-stat strong,
.graph-fact strong {
  font-family: 'JetBrains Mono', Consolas, monospace;
}

.score-orbit {
  min-height: 560px;
  padding: 0;
  overflow: hidden;
  background:
    radial-gradient(circle at 50% 42%, rgba(77, 214, 255, 0.18), transparent 34%),
    linear-gradient(180deg, rgba(12, 24, 39, 0.94), rgba(5, 8, 13, 0.96));
}

.risk-stage {
  position: absolute;
  inset: 0;
}

#risk-3d {
  width: 100%;
  height: 100%;
  display: block;
}

.score-ring {
  position: absolute;
  right: 28px;
  bottom: 28px;
  width: 220px;
  background:
    radial-gradient(circle at center, rgba(5, 8, 13, 0.94) 0 57%, transparent 57% 100%),
    conic-gradient(from -90deg, var(--accent) calc(var(--score) * 1%), rgba(255, 255, 255, 0.1) 0);
  backdrop-filter: blur(10px);
}

.score-copy strong {
  font-family: 'JetBrains Mono', Consolas, monospace;
  font-size: clamp(2rem, 3vw, 3rem);
}

.hero-notes {
  min-height: 0;
}

.section-head h2,
.detail-title-row h3 {
  font-family: 'IBM Plex Sans', 'Segoe UI', sans-serif;
  letter-spacing: 0;
}

.dataset-grid {
  grid-template-columns: repeat(7, minmax(0, 1fr));
}

.dataset-card {
  border-radius: 14px;
  min-height: 190px;
}

.dataset-card .auc strong {
  font-family: 'JetBrains Mono', Consolas, monospace;
  font-size: 1.55rem;
}

.track span,
.dist-track span {
  background: linear-gradient(90deg, var(--accent), var(--accent-2));
}

.profile-grid {
  grid-template-columns: 1.05fr 1.05fr 0.9fr 1.25fr;
}

.sample-table th {
  color: #061217;
  background: var(--accent);
}

.graph-layout {
  grid-template-columns: minmax(360px, 0.85fr) minmax(0, 1.15fr);
}

.flow-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.board-grid,
.story-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.reference-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.caveat-list {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

@media (max-width: 1240px) {
  .dataset-grid,
  .profile-grid,
  .board-grid,
  .story-grid,
  .reference-grid,
  .caveat-list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 880px) {
  html,
  body {
    max-width: 100%;
    overflow-x: hidden;
  }

  .shell {
    width: min(100vw - 24px, 1420px);
    overflow: hidden;
  }

  .hero,
  .dataset-grid,
  .detail-wrap,
  .profile-grid,
  .graph-layout,
  .flow-grid,
  .graph-facts,
  .board-grid,
  .story-grid,
  .scenario-grid,
  .policy-grid,
  .investigation-layout,
  .reference-grid,
  .caveat-list {
    grid-template-columns: 1fr;
  }

  .profile-panel,
  .profile-block,
  .detail-panel,
  .detail-side {
    min-width: 0;
  }

  .profile-block {
    width: 100%;
  }

  .hero-panel {
    min-height: auto;
    padding: 22px;
  }

  .score-orbit {
    min-height: 420px;
  }

  .graph-stage {
    overflow: hidden;
  }

  .graph-stage svg {
    max-width: 100%;
  }

  .graph-stage svg text {
    display: none;
  }

  .sample-table-wrap {
    max-width: 100%;
  }

  .sample-table {
    min-width: 520px;
  }
}
"""


HTML_SCRIPT = """
const payload = JSON.parse(document.getElementById('dashboard-data').textContent);
const state = {
  selectedDataset: payload.datasets.find((item) => item.key === payload.meta.primaryDataset)?.key || payload.datasets[0]?.key,
  selectedCase: payload.investigation?.cases?.[0]?.caseId || null,
};

const formatNumber = (value, approximate = false) => {
  if (typeof value !== 'number') {
    return value;
  }
  const text = new Intl.NumberFormat('en-US').format(value);
  return approximate ? `~${text}` : text;
};

const formatRatio = (value) => `${(value * 100).toFixed(2)}%`;

const formatAucFill = (value) => {
  if (typeof value !== 'number') {
    return 0;
  }
  return Math.max(0, Math.min(1, (value - 0.6) / 0.4));
};

const formatAucText = (value) => {
  if (typeof value !== 'number') {
    return '暂未评估';
  }
  return value.toFixed(6);
};

const nodeColor = (label) => {
  if (label === 1) return '#ff7c6b';
  if (label === 0) return '#8ee0c8';
  if (label === 2) return '#f2b35d';
  return '#6f8f97';
};

const createMetricCards = (items) => items.map((item) => `
  <div class="mini-stat">
    <span>${item.label}</span>
    <strong>${item.type === 'ratio' ? formatRatio(item.value) : formatNumber(item.value, item.approximate)}</strong>
  </div>
`).join('');

const createAnnotationCards = (items) => items.map((item) => `
  <div class="annotation">
    <span>${item.label}</span>
    <strong>${item.value}</strong>
  </div>
`).join('');

const createDistributionBars = (items) => {
  const total = items.reduce((sum, item) => sum + (Number(item.value) || 0), 0);
  return items.map((item) => {
    const value = Number(item.value) || 0;
    const ratio = total > 0 ? value / total : 0;
    return `
      <div class="dist-row">
        <div class="dist-label">
          <span>${item.label}</span>
          <strong>${formatNumber(value)}</strong>
        </div>
        <div class="dist-track">
          <span style="width:${Math.max(1, ratio * 100).toFixed(2)}%; background:${item.color || 'var(--accent-2)'}"></span>
        </div>
      </div>
    `;
  }).join('');
};

const createSchemaList = (items) => items.map((item) => `
  <span class="schema-chip">
    <strong>${item.name}</strong>
    <small>${item.detail}</small>
  </span>
`).join('');

const createSampleTable = (sample) => {
  if (!sample || !sample.columns || !sample.rows || sample.rows.length === 0) {
    return '<p class="empty-note">暂无可展示的样本预览。</p>';
  }
  return `
    <div class="sample-table-wrap">
      <table class="sample-table">
        <thead>
          <tr>${sample.columns.map((column) => `<th>${column}</th>`).join('')}</tr>
        </thead>
        <tbody>
          ${sample.rows.map((row) => `
            <tr>${sample.columns.map((column) => `<td>${row[column] ?? ''}</td>`).join('')}</tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  `;
};

const renderHero = () => {
  document.getElementById('hero-eyebrow').textContent = payload.meta.eyebrow;
  document.getElementById('hero-title').textContent = payload.meta.title;
  document.getElementById('hero-intro').textContent = payload.meta.intro;
  document.getElementById('score-ring').style.setProperty('--score', (payload.meta.primaryAuc * 100).toFixed(1));
  document.getElementById('score-value').textContent = formatAucText(payload.meta.primaryAuc);
  document.getElementById('score-label').textContent = payload.meta.primaryLabel;
  document.getElementById('score-note').textContent = payload.meta.primaryNote;
  document.getElementById('generated-at').textContent = payload.meta.generatedAt;
  document.getElementById('project-mode').textContent = payload.meta.mode;
  document.getElementById('stack-name').textContent = payload.meta.stack;
  document.getElementById('hero-stats').innerHTML = payload.heroStats.map((item) => `
    <div class="hero-stat">
      <span class="label">${item.label}</span>
      <strong>${item.value}</strong>
      <small>${item.note}</small>
    </div>
  `).join('');
  document.getElementById('hero-notes-list').innerHTML = payload.heroNotes.map((item) => `<li>${item}</li>`).join('');
};

const renderDatasetCards = () => {
  const root = document.getElementById('dataset-grid');
  root.innerHTML = payload.datasets.map((dataset) => `
    <button class="dataset-card ${dataset.key === state.selectedDataset ? 'active' : ''}" type="button" data-dataset-key="${dataset.key}">
      <span class="tagline">${dataset.tagline}</span>
      <h3>${dataset.name}</h3>
      <span class="mode">${dataset.modality}</span>
      <span class="auc">
        <strong>${formatAucText(dataset.trustedAuc)}</strong>
      </span>
      <div class="track" style="--fill: ${formatAucFill(dataset.trustedAuc)}">
        <span></span>
      </div>
      <span class="trust" style="margin-top: 12px;">${dataset.trustLine}</span>
    </button>
  `).join('');

  root.querySelectorAll('.dataset-card').forEach((button) => {
    button.addEventListener('click', () => {
      state.selectedDataset = button.dataset.datasetKey;
      renderDatasetCards();
      renderDatasetDetail();
    });
  });
};

const renderDatasetDetail = () => {
  const dataset = payload.datasets.find((item) => item.key === state.selectedDataset);
  if (!dataset) {
    return;
  }

  document.getElementById('detail-kicker').textContent = dataset.tagline;
  document.getElementById('detail-title').textContent = dataset.name;
  document.getElementById('detail-summary').textContent = dataset.summary;
  document.getElementById('detail-badges').innerHTML = dataset.badges.map((badge) => `<span class="badge">${badge}</span>`).join('');
  document.getElementById('detail-metrics').innerHTML = createMetricCards(dataset.metrics);
  document.getElementById('detail-annotations').innerHTML = createAnnotationCards(dataset.annotations);
  document.getElementById('detail-availability').textContent = dataset.availability;
  document.getElementById('detail-trust').textContent = dataset.trustNote;
  document.getElementById('detail-caution').textContent = dataset.caution;
  document.getElementById('detail-features').innerHTML = dataset.topFeatures.map((item) => `<li>${item}</li>`).join('');
  document.getElementById('profile-distribution-title').textContent = dataset.profile.distributionTitle;
  document.getElementById('profile-distribution').innerHTML = createDistributionBars(dataset.profile.distribution);
  document.getElementById('profile-splits-title').textContent = dataset.profile.splitTitle;
  document.getElementById('profile-splits').innerHTML = createDistributionBars(dataset.profile.splits);
  document.getElementById('profile-schema').innerHTML = createSchemaList(dataset.profile.schema);
  document.getElementById('profile-sample-title').textContent = dataset.profile.sampleTitle;
  document.getElementById('profile-sample').innerHTML = createSampleTable(dataset.profile.sample);
};

const renderGraph = () => {
  const graph = payload.graphSample;
  document.getElementById('graph-title').textContent = graph.title;
  document.getElementById('graph-description').textContent = graph.description;
  document.getElementById('graph-facts').innerHTML = graph.metrics.map((item) => `
    <div class="graph-fact">
      <span>${item.label}</span>
      <strong>${item.value}</strong>
    </div>
  `).join('');
  document.getElementById('graph-annotation').textContent = graph.annotation;
  document.getElementById('graph-legend').innerHTML = graph.legend.map((item) => `
    <span class="legend-item"><span class="legend-swatch" style="background:${item.color}"></span>${item.label}</span>
  `).join('');

  const width = 720;
  const height = 500;
  const cx = 360;
  const cy = 250;
  const radiusX = 240;
  const radiusY = 170;
  const positions = new Map();
  positions.set(graph.focusNode.id, { x: cx, y: cy });

  const others = graph.nodes.filter((node) => node.id !== graph.focusNode.id);
  others.forEach((node, index) => {
    const angle = (-Math.PI / 2) + (Math.PI * 2 * index / others.length);
    positions.set(node.id, {
      x: cx + Math.cos(angle) * radiusX,
      y: cy + Math.sin(angle) * radiusY,
    });
  });

  const edgeMarkup = graph.edges.map((edge) => {
    const from = positions.get(edge.source);
    const to = positions.get(edge.target);
    return `
      <line x1="${from.x}" y1="${from.y}" x2="${to.x}" y2="${to.y}"
        stroke="rgba(242,179,93,0.38)" stroke-width="2" />
    `;
  }).join('');

  const nodeMarkup = graph.nodes.map((node) => {
    const point = positions.get(node.id);
    const label = node.id === graph.focusNode.id ? `risk ${node.id}` : String(node.id);
    const radius = node.id === graph.focusNode.id ? 20 : 11;
    const glow = node.id === graph.focusNode.id ? 34 : 0;
    return `
      <g>
        ${glow ? `<circle cx="${point.x}" cy="${point.y}" r="${glow}" fill="rgba(255,124,107,0.12)" />` : ''}
        <circle cx="${point.x}" cy="${point.y}" r="${radius}" fill="${nodeColor(node.label)}" stroke="rgba(255,255,255,0.9)" stroke-width="${node.id === graph.focusNode.id ? 2 : 1.2}" />
        <text x="${point.x}" y="${point.y + radius + 18}" fill="#dbe6e2" text-anchor="middle" font-size="12" font-family="'JetBrains Mono', monospace">${label}</text>
      </g>
    `;
  }).join('');

  document.getElementById('graph-svg').innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${graph.title}">
      <defs>
        <filter id="softGlow">
          <feGaussianBlur stdDeviation="8" result="blur"></feGaussianBlur>
          <feMerge>
            <feMergeNode in="blur"></feMergeNode>
            <feMergeNode in="SourceGraphic"></feMergeNode>
          </feMerge>
        </filter>
      </defs>
      <rect x="10" y="10" width="${width - 20}" height="${height - 20}" rx="22" fill="rgba(255,255,255,0.02)" stroke="rgba(255,255,255,0.05)" />
      ${edgeMarkup}
      ${nodeMarkup}
    </svg>
  `;
};

const renderFlow = () => {
  document.getElementById('flow-grid').innerHTML = payload.inferenceFlow.map((item) => `
    <div class="flow-step">
      <span class="step-id">${item.step}</span>
      <h4>${item.title}</h4>
      <p>${item.body}</p>
    </div>
  `).join('');
};

const renderScenarioFlow = (scenario) => {
  const positions = new Map();
  const width = 320;
  const height = 82;
  scenario.nodes.forEach((node, index) => {
    const angle = (Math.PI * 2 * index) / scenario.nodes.length - Math.PI / 2;
    positions.set(node, {
      x: 160 + Math.cos(angle) * 104,
      y: 41 + Math.sin(angle) * 26,
    });
  });
  const edges = scenario.edges.map(([source, target]) => {
    const from = positions.get(source);
    const to = positions.get(target);
    return `<line x1="${from.x}" y1="${from.y}" x2="${to.x}" y2="${to.y}" stroke="rgba(215,255,114,0.34)" stroke-width="2" />`;
  }).join('');
  const nodes = scenario.nodes.map((node, index) => {
    const point = positions.get(node);
    const isAnchor = index === 0 || node === 'M' || node === 'S';
    return `
      <g>
        <circle cx="${point.x}" cy="${point.y}" r="${isAnchor ? 9 : 7}" fill="${isAnchor ? '#ff7c6b' : '#4dd6ff'}" />
        <text x="${point.x}" y="${point.y + 23}" text-anchor="middle" fill="#dbe6e2" font-size="10" font-family="'JetBrains Mono', monospace">${node}</text>
      </g>
    `;
  }).join('');
  return `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${scenario.name}">${edges}${nodes}</svg>`;
};

const renderFraudScenarios = () => {
  document.getElementById('scenario-grid').innerHTML = payload.fraudScenarios.map((scenario) => `
    <article class="scenario-card">
      <header>
        <h4>${scenario.name}</h4>
        <span class="status-chip">${scenario.riskLevel}</span>
      </header>
      <p>${scenario.pattern}</p>
      <div class="scenario-flow">${renderScenarioFlow(scenario)}</div>
      <p>${scenario.signal}</p>
      <p>${scenario.modelResponse}</p>
      <button class="scenario-action" type="button" data-scenario="${scenario.name}">生成仿真事件</button>
      <div class="scenario-result" hidden>
        <div>
          <span>仿真事件</span>
          <strong>${scenario.generatedCase.event}</strong>
        </div>
        <div>
          <span>模型识别结果</span>
          <strong>${scenario.generatedCase.decision} / score ${scenario.generatedCase.riskScore.toFixed(2)}</strong>
        </div>
        <p>${scenario.generatedCase.summary}</p>
      </div>
      <div class="graph-facts">
        ${scenario.stats.map((item) => `
          <div class="graph-fact">
            <span>${item.label}</span>
            <strong>${item.value}</strong>
          </div>
        `).join('')}
      </div>
    </article>
  `).join('');
  document.querySelectorAll('.scenario-action').forEach((button) => {
    button.addEventListener('click', () => {
      const result = button.nextElementSibling;
      result.hidden = !result.hidden;
      button.textContent = result.hidden ? '生成仿真事件' : '收起识别结果';
    });
  });
};

const renderPolicy = () => {
  const policy = payload.policy;
  document.getElementById('policy-grid').innerHTML = `
    <article class="policy-card">
      <span>模型版本</span>
      <strong>${policy.model.version}</strong>
      <span style="margin-top:12px;">训练数据</span>
      <strong>${policy.model.dataset} / AUC ${formatAucText(policy.model.auc)}</strong>
    </article>
    <article class="policy-card">
      <span>风险阈值策略</span>
      <div class="threshold-list">
        ${policy.thresholds.map((item) => `
          <div class="threshold-item">
            <span>${item.level}</span>
            <strong>${item.threshold.toFixed(2)}</strong>
            <span>${item.action}</span>
            <span>命中 ${formatNumber(item.hitCount)} 条</span>
          </div>
        `).join('')}
      </div>
    </article>
    <article class="policy-card">
      <span>可审计预测记录</span>
      <strong>${policy.batch.output}</strong>
      <span style="margin-top:12px;">策略更新时间</span>
      <strong>${policy.model.updatedAt}</strong>
    </article>
  `;
};

const caseLevelColor = (level) => {
  if (level === 'critical') return '#ff7c6b';
  if (level === 'high') return '#f2b35d';
  if (level === 'medium') return '#d7ff72';
  return '#8ee0c8';
};

const renderTraceCanvas = (caseItem) => {
  const trace = caseItem.trace;
  const width = 760;
  const height = 280;
  const cx = 190;
  const cy = 140;
  const neighbors = [
    { label: '欺诈邻居', count: trace.fraudNeighborCount, color: '#ff7c6b' },
    { label: '正常邻居', count: trace.normalNeighborCount, color: '#8ee0c8' },
    { label: '背景节点', count: trace.backgroundNeighborCount, color: '#f2b35d' },
  ].filter((item) => item.count > 0);
  const total = Math.max(1, trace.neighborCount);
  const neighborNodes = [];
  neighbors.forEach((group, groupIndex) => {
    const visible = Math.min(group.count, 8);
    for (let index = 0; index < visible; index += 1) {
      neighborNodes.push({ ...group, groupIndex, localIndex: index });
    }
  });
  const nodeMarkup = neighborNodes.map((node, index) => {
    const angle = -Math.PI / 2 + (Math.PI * 2 * index) / Math.max(1, neighborNodes.length);
    const x = cx + Math.cos(angle) * 118;
    const y = cy + Math.sin(angle) * 90;
    return `
      <line x1="${cx}" y1="${cy}" x2="${x}" y2="${y}" stroke="rgba(215,255,114,0.28)" stroke-width="1.8" />
      <circle cx="${x}" cy="${y}" r="9" fill="${node.color}" />
    `;
  }).join('');
  const legend = neighbors.map((item, index) => `
    <g transform="translate(430 ${78 + index * 32})">
      <circle cx="0" cy="0" r="7" fill="${item.color}" />
      <text x="16" y="5" fill="#dbe6e2" font-size="14">${item.label} ${item.count}</text>
    </g>
  `).join('');
  return `
    <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="案件溯源结构">
      <rect x="12" y="12" width="${width - 24}" height="${height - 24}" rx="18" fill="rgba(255,255,255,0.02)" stroke="rgba(255,255,255,0.06)" />
      ${nodeMarkup}
      <circle cx="${cx}" cy="${cy}" r="24" fill="${caseLevelColor(caseItem.riskLevel)}" />
      <text x="${cx}" y="${cy + 48}" text-anchor="middle" fill="#dbe6e2" font-size="13">focus ${caseItem.focusNode}</text>
      <text x="430" y="42" fill="#edf3ef" font-size="16" font-weight="600">一跳邻域摘要</text>
      ${legend}
      <text x="430" y="196" fill="#9aaab0" font-size="13">关联边 ${trace.incidentEdgeCount} / 主导交易类型 ${trace.dominantEdgeType}</text>
      <text x="430" y="222" fill="#9aaab0" font-size="13">时间跨度 ${trace.timeSpan} / 邻居覆盖 ${trace.neighborCount} 个节点</text>
      <text x="430" y="248" fill="#9aaab0" font-size="13">主导类型占比 ${(trace.dominantEdgeTypeShare * 100).toFixed(1)}%</text>
    </svg>
  `;
};

const renderCaseDetail = () => {
  const cases = payload.investigation.cases || [];
  const caseItem = cases.find((item) => item.caseId === state.selectedCase) || cases[0];
  if (!caseItem) {
    document.getElementById('case-kicker').textContent = '暂无风险事件';
    document.getElementById('case-title').textContent = '请先运行流式原型';
    document.getElementById('case-status').textContent = '未生成';
    document.getElementById('case-metrics').innerHTML = '';
    document.getElementById('case-process').innerHTML = '';
    document.getElementById('trace-canvas').innerHTML = '<p class="empty-note" style="padding:18px;">缺少 output/streaming 产物。</p>';
    document.getElementById('audit-list').innerHTML = '';
    return;
  }
  state.selectedCase = caseItem.caseId;
  document.getElementById('case-kicker').textContent = `事件 ${caseItem.eventId} / ${caseItem.channel}`;
  document.getElementById('case-title').textContent = `${caseItem.caseId}  焦点节点 ${caseItem.focusNode}`;
  document.getElementById('case-status').textContent = caseItem.status;
  document.getElementById('case-metrics').innerHTML = createMetricCards([
    { label: '风险分', value: caseItem.riskScore },
    { label: '风险等级', value: caseItem.riskLevel },
    { label: '建议动作', value: caseItem.action },
    { label: '交易金额', value: caseItem.amount },
  ]);
  document.getElementById('case-process').innerHTML = `
    <div class="case-process-item">
      <span>处理状态</span>
      ${caseItem.status}
    </div>
    <div class="case-process-item">
      <span>复核结论</span>
      ${caseItem.review}
    </div>
    <div class="case-process-item">
      <span>风险解释</span>
      ${caseItem.explanation}
    </div>
  `;
  document.getElementById('trace-canvas').innerHTML = renderTraceCanvas(caseItem);
  document.getElementById('audit-list').innerHTML = caseItem.audit.map((item, index) => `
    <div class="audit-item">
      <span>审计记录 ${String(index + 1).padStart(2, '0')}</span>
      ${item}
    </div>
  `).join('');
  document.querySelectorAll('.case-button').forEach((button) => {
    button.classList.toggle('active', button.dataset.caseId === caseItem.caseId);
  });
};

const renderInvestigation = () => {
  const investigation = payload.investigation;
  const cases = investigation.cases || [];
  document.getElementById('case-list').innerHTML = cases.map((item) => `
    <button class="case-button ${item.caseId === state.selectedCase ? 'active' : ''}" type="button" data-case-id="${item.caseId}">
      <span>${item.status}</span>
      <strong><span>${item.caseId}</span><span style="color:${caseLevelColor(item.riskLevel)}">${item.riskLevel}</span></strong>
      <span>score ${item.riskScore.toFixed(4)} / action ${item.action}</span>
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

const renderBoard = () => {
  document.getElementById('board-grid').innerHTML = payload.implementation.map((item) => `
    <article class="status-card">
      <header>
        <h4>${item.title}</h4>
        <span class="status-chip">${item.status}</span>
      </header>
      <p>${item.detail}</p>
    </article>
  `).join('');

  document.getElementById('caveat-list').innerHTML = payload.caveats.map((item) => `
    <article class="caveat">
      <strong>${item.title}</strong>
      ${item.body}
    </article>
  `).join('');
};

const renderScoringStories = () => {
  document.getElementById('story-grid').innerHTML = payload.scoringStories.map((item) => `
    <article class="status-card">
      <header>
        <h4>${item.title}</h4>
        <span class="status-chip">${item.tag}</span>
      </header>
      <p>${item.detail}</p>
    </article>
  `).join('');
};

const renderReferenceInsights = () => {
  document.getElementById('reference-grid').innerHTML = payload.referenceInsights.map((item) => `
    <article class="reference-card">
      <h4>${item.source}</h4>
      <div class="reference-block">
        <span>公开方案能力</span>
        <p>${item.good}</p>
      </div>
      <div class="reference-block">
        <span>本系统实现</span>
        <p>${item.absorbed}</p>
      </div>
      <div class="reference-block">
        <span>展示亮点</span>
        <p>${item.gap}</p>
      </div>
    </article>
  `).join('');
};

const renderSources = () => {
  document.getElementById('sources-list').innerHTML = payload.sources.map((item) => `<li>${item}</li>`).join('');
};

const renderRiskScene = () => {
  const canvas = document.getElementById('risk-3d');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const orbitCount = 54;
  const links = [];
  const nodes = Array.from({ length: orbitCount }, (_, index) => {
    const band = index % 3;
    const angle = (Math.PI * 2 * index) / orbitCount;
    const radius = 120 + band * 54 + ((index * 17) % 24);
    return {
      angle,
      radius,
      z: Math.sin(index * 1.7) * 90,
      risk: index % 11 === 0 || index % 17 === 0,
    };
  });
  for (let index = 0; index < nodes.length; index += 1) {
    links.push([index, (index + 7) % nodes.length]);
    if (index % 6 === 0) links.push([index, (index + 19) % nodes.length]);
  }

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
    const cy = rect.height * 0.47;
    const t = time * 0.00018;
    const projected = nodes.map((node) => {
      const x3 = Math.cos(node.angle + t) * node.radius;
      const y3 = Math.sin(node.angle + t * 0.72) * node.radius * 0.52;
      const z3 = node.z + Math.sin(t * 3 + node.angle) * 36;
      const scale = 520 / (620 - z3);
      return {
        x: cx + x3 * scale,
        y: cy + y3 * scale,
        s: scale,
        risk: node.risk,
        alpha: Math.max(0.22, Math.min(0.9, scale * 0.9)),
      };
    });

    const gradient = ctx.createRadialGradient(cx, cy, 20, cx, cy, Math.min(rect.width, rect.height) * 0.48);
    gradient.addColorStop(0, 'rgba(77, 214, 255, 0.20)');
    gradient.addColorStop(1, 'rgba(77, 214, 255, 0)');
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, rect.width, rect.height);

    ctx.lineWidth = 1;
    links.forEach(([a, b]) => {
      const from = projected[a];
      const to = projected[b];
      const strong = from.risk || to.risk;
      ctx.strokeStyle = strong ? 'rgba(215,255,114,0.22)' : 'rgba(77,214,255,0.16)';
      ctx.beginPath();
      ctx.moveTo(from.x, from.y);
      ctx.lineTo(to.x, to.y);
      ctx.stroke();
    });

    projected.forEach((node) => {
      const r = (node.risk ? 4.6 : 2.8) * node.s;
      ctx.beginPath();
      ctx.fillStyle = node.risk ? `rgba(255,107,122,${node.alpha})` : `rgba(77,214,255,${node.alpha})`;
      ctx.arc(node.x, node.y, Math.max(1.8, r), 0, Math.PI * 2);
      ctx.fill();
    });

    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(-0.18);
    ctx.strokeStyle = 'rgba(215,255,114,0.22)';
    ctx.lineWidth = 1.2;
    ctx.strokeRect(-rect.width * 0.31, -rect.height * 0.25, rect.width * 0.62, rect.height * 0.5);
    ctx.restore();

    requestAnimationFrame(draw);
  };
  requestAnimationFrame(draw);
};

renderHero();
renderRiskScene();
renderScoringStories();
renderReferenceInsights();
renderFraudScenarios();
renderPolicy();
renderInvestigation();
renderDatasetCards();
renderDatasetDetail();
renderGraph();
renderFlow();
renderBoard();
renderSources();
"""
