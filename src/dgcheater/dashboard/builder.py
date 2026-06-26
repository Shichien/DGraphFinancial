from __future__ import annotations

from datetime import datetime
from pathlib import Path
import csv
import json

import numpy as np
import pandas as pd

from ..core.config import APP_CONFIG, DEFAULT_OUTPUT_DIR
from ..streaming.event_store import RiskEventStore, default_sqlite_path
from .assets import HTML_SCRIPT, HTML_STYLE, REFRESH_STYLE


def build_showcase_dashboard(
    output_path: Path = APP_CONFIG.dashboard.output_path,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> Path:
    payload = _build_payload(output_dir)
    html = _render_html(payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path


def _render_html(payload: dict[str, object]) -> str:
    payload_json = json.dumps(_json_safe(payload), ensure_ascii=False, allow_nan=False).replace("</", "<\\/")
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="zh-CN">',
            "<head>",
            '  <meta charset="utf-8" />',
            '  <meta name="viewport" content="width=device-width, initial-scale=1" />',
            "  <title>DGCheater Showcase Dashboard</title>",
            f"  <style>{HTML_STYLE}{REFRESH_STYLE}</style>",
            "</head>",
            "<body>",
            '  <a class="skip-link" href="#datasets">跳到数据资产概览</a>',
            '  <div class="shell">',
            '    <header class="topbar fade" data-delay="1">',
            '      <div class="brand">',
            '        <div class="brand-mark">DG</div>',
            '        <div class="brand-copy">',
            '          <strong>DGCheater</strong>',
            "          <span>Graph Risk Intelligence</span>",
            "        </div>",
            "      </div>",
            '      <div class="topbar-meta">',
            '        <span class="pill" id="generated-at"></span>',
            '        <span class="pill" id="project-mode"></span>',
            '        <span class="pill" id="stack-name"></span>',
            "      </div>",
            "    </header>",
            '    <main>',
            '      <section class="hero" aria-label="项目总览">',
            '        <article class="hero-panel fade" data-delay="2">',
            '          <span class="eyebrow" id="hero-eyebrow"></span>',
            '          <h1 id="hero-title"></h1>',
            '          <p class="hero-intro" id="hero-intro"></p>',
            '          <div class="hero-grid" id="hero-stats"></div>',
            "        </article>",
            '        <div class="hero-side">',
            '          <article class="hero-panel score-orbit fade" data-delay="3">',
            '            <div class="risk-stage" aria-hidden="true">',
            '              <canvas id="risk-3d"></canvas>',
            "            </div>",
            '            <div class="score-ring" id="score-ring">',
            '              <div class="score-copy">',
            '                <span class="meta" id="score-label"></span>',
            '                <strong id="score-value"></strong>',
            '                <small id="score-note"></small>',
            "              </div>",
            "            </div>",
            "          </article>",
            '          <article class="panel hero-notes fade" data-delay="4">',
            "            <h2>系统定位</h2>",
            '            <ul id="hero-notes-list"></ul>',
            "          </article>",
            "        </div>",
            "      </section>",
            '      <section class="section fade" data-delay="2">',
            '        <div class="section-head">',
            '          <div>',
            "            <h2>方案能力</h2>",
            "            <p>围绕评估可信性、结构特征增益、跨数据迁移、解释能力和工程交付能力展示系统完整性。</p>",
            "          </div>",
            "        </div>",
            '        <article class="board">',
            '          <div class="story-grid" id="story-grid"></div>',
            "        </article>",
            "      </section>",
            '      <section class="section fade" data-delay="2">',
            '        <div class="section-head">',
            '          <div>',
            "            <h2>公开方案对照</h2>",
            "            <p>对比公开实现，展示本系统在数据口径、特征建模、流式风险和案件处置上的补强。</p>",
            "          </div>",
            "        </div>",
            '        <article class="reference-panel">',
            '          <div class="reference-grid" id="reference-grid"></div>',
            "        </article>",
            "      </section>",
            '      <section class="section fade" data-delay="2" id="datasets">',
            '        <div class="section-head">',
            '          <div>',
            "            <h2>数据资产概览</h2>",
            "            <p>统一展示公开图基准、表格交易数据和仿真样例，便于评估输入结构、标签分布和验证口径。</p>",
            "          </div>",
            "        </div>",
            '        <div class="dataset-grid" id="dataset-grid"></div>',
            '        <div class="detail-wrap">',
            '          <article class="detail-panel">',
            '            <span class="detail-kicker" id="detail-kicker"></span>',
            '            <div class="detail-title-row">',
            '              <h3 id="detail-title"></h3>',
            '              <div class="detail-badges" id="detail-badges"></div>',
            "            </div>",
            '            <p class="detail-summary" id="detail-summary"></p>',
            '            <div class="detail-metrics" id="detail-metrics"></div>',
            '            <div class="detail-annotations" id="detail-annotations"></div>',
            "          </article>",
            '          <aside class="detail-side">',
            "            <h3>数据档案</h3>",
            '            <div class="side-block">',
            "              <span>数据状态</span>",
            '              <p id="detail-availability"></p>',
            "            </div>",
            '            <div class="side-block">',
            "              <span>可信口径</span>",
            '              <p id="detail-trust"></p>',
            "            </div>",
            '            <div class="side-block">',
            "              <span>适用范围</span>",
            '              <p id="detail-caution"></p>',
            "            </div>",
            '            <div class="side-block">',
            "              <span>关键特征</span>",
            '              <ul class="detail-top-features" id="detail-features"></ul>',
            "            </div>",
            "          </aside>",
            "        </div>",
            '        <article class="profile-panel">',
            '          <div class="profile-grid">',
            '            <section class="profile-block">',
            '              <h3 id="profile-distribution-title"></h3>',
            '              <div id="profile-distribution"></div>',
            "            </section>",
            '            <section class="profile-block">',
            '              <h3 id="profile-splits-title"></h3>',
            '              <div id="profile-splits"></div>',
            "            </section>",
            '            <section class="profile-block">',
            "              <h3>字段结构</h3>",
            '              <div class="schema-list" id="profile-schema"></div>',
            "            </section>",
            '            <section class="profile-block">',
            '              <h3 id="profile-sample-title"></h3>',
            '              <div id="profile-sample"></div>',
            "            </section>",
            "          </div>",
            "        </article>",
            "      </section>",
            '      <section class="section fade" data-delay="3">',
            '        <div class="section-head">',
            '          <div>',
            "            <h2>仿真欺诈剧本</h2>",
            "            <p>覆盖循环转账、分散汇集、集中转出和账户团伙四类高风险交易链路。</p>",
            "          </div>",
            "        </div>",
            '        <article class="scenario-panel">',
            '          <div class="scenario-grid" id="scenario-grid"></div>',
            "        </article>",
            "      </section>",
            '      <section class="section fade" data-delay="3">',
            '        <div class="section-head">',
            '          <div>',
            "            <h2>调查控制台</h2>",
            "            <p>基于流式风险事件构建案件处置视图，联动展示风险等级、建议动作、复核状态、审计记录和一跳溯源结构。</p>",
            "          </div>",
            "        </div>",
            '        <article class="investigation-panel">',
            '          <div class="policy-grid" id="policy-grid"></div>',
            '          <div class="investigation-layout">',
            '            <div class="case-list" id="case-list"></div>',
            '            <div class="case-detail">',
            '              <div class="case-detail-head">',
            '                <div>',
            '                  <span class="detail-kicker" id="case-kicker"></span>',
            '                  <h3 id="case-title"></h3>',
            "                </div>",
            '                <span class="status-chip" id="case-status"></span>',
            "              </div>",
            '              <div class="case-metrics" id="case-metrics"></div>',
            '              <div class="case-process" id="case-process"></div>',
            '              <div class="trace-canvas" id="trace-canvas"></div>',
            '              <div class="audit-list" id="audit-list"></div>',
            "            </div>",
            "          </div>",
            "        </article>",
            "      </section>",
            '      <section class="section fade" data-delay="3">',
            '        <div class="section-head">',
            '          <div>',
            "            <h2>匿名风险关系网络</h2>",
            "            <p>基于本地 DGraph-Fin 抽取高风险节点的一跳关系结构，展示图特征如何刻画欺诈节点周边的交易行为模式。</p>",
            "          </div>",
            "        </div>",
            '        <article class="graph-panel">',
            '          <div class="graph-layout">',
            '            <div class="graph-stage">',
            '              <div id="graph-svg"></div>',
            "            </div>",
            '            <div class="graph-copy">',
            '              <h3 id="graph-title"></h3>',
            '              <p id="graph-description"></p>',
            '              <div class="graph-facts" id="graph-facts"></div>',
            '              <p id="graph-annotation"></p>',
            '              <div class="legend" id="graph-legend"></div>',
            "            </div>",
            "          </div>",
            "        </article>",
            "      </section>",
            '      <section class="section fade" data-delay="4">',
            '        <div class="section-head">',
            '          <div>',
            "            <h2>推理链路</h2>",
            "            <p>从数据接入、图特征构建、模型融合到风险输出，展示系统在离线训练和在线识别中的主要处理流程。</p>",
            "          </div>",
            "        </div>",
            '        <article class="flow-panel">',
            '          <div class="flow-grid" id="flow-grid"></div>',
            "        </article>",
            "      </section>",
            '      <section class="section fade" data-delay="5">',
            '        <div class="section-head">',
            '          <div>',
            "            <h2>交付证据</h2>",
            "            <p>汇总模型、数据、可视化、流式处理和性能验证的交付证据。</p>",
            "          </div>",
            "        </div>",
            '        <article class="board">',
            '          <div class="board-grid" id="board-grid"></div>',
            "        </article>",
            "      </section>",
            '      <section class="section fade" data-delay="5">',
            '        <div class="section-head">',
            '          <div>',
            "            <h2>评估口径</h2>",
            "            <p>列出关键数据集的验证方式和分数解释口径，保证结果可复核。</p>",
            "          </div>",
            "        </div>",
            '        <div class="caveat-list" id="caveat-list"></div>',
            "      </section>",
            '      <section class="section fade" data-delay="5">',
            '        <article class="sources">',
            "          <h3>数据来源</h3>",
            "          <p>展示页引用的实验指标、公开数据摘要和工程产物。</p>",
            '          <ul id="sources-list"></ul>',
            "        </article>",
            "      </section>",
            "    </main>",
            "  </div>",
            f'  <script id="dashboard-data" type="application/json">{payload_json}</script>',
            f"  <script>{HTML_SCRIPT}</script>",
            "</body>",
            "</html>",
        ]
    )


def _build_payload(output_dir: Path) -> dict[str, object]:
    datasets = _build_dataset_payloads(output_dir)
    primary_dataset = next(item for item in datasets if item["key"] == "dgraph_fin")
    return {
        "meta": {
            "eyebrow": "Graph Fraud Intelligence Platform",
            "title": "金融反欺诈风险识别系统",
            "intro": (
                "面向大规模交易关系网络，融合节点画像、交易时序、关系结构与风险邻域信号，实现欺诈用户识别、风险解释和在线处置链路展示。"
            ),
            "generatedAt": f"生成时间 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "mode": "赛道一作品展示",
            "stack": "图结构特征 + 双模型融合",
            "primaryDataset": "dgraph_fin",
            "primaryAuc": primary_dataset["trustedAuc"],
            "primaryLabel": "验证 AUC",
            "primaryNote": "DGraph-Fin 公开基准验证结果",
        },
        "heroStats": [
            {
                "label": "DGraph-Fin AUC",
                "value": f"{primary_dataset['trustedAuc']:.6f}",
                "note": "基于公开图基准训练与验证切分",
            },
            {
                "label": "数据覆盖",
                "value": "7 个",
                "note": "覆盖图数据、表格交易数据和仿真样例",
            },
            {
                "label": "图特征规模",
                "value": "126 维",
                "note": "节点属性、关系结构、交易类型和时间统计统一建模",
            },
        ],
        "heroNotes": [
            "系统围绕欺诈用户识别、风险解释和流式处置三个环节构建完整闭环。",
            "特征工程严格限定在可用输入范围内，降低标签泄漏或未来信息导致的评估偏差。",
            "多数据集结果验证图数据、表格交易和仿真样例的统一接入能力。",
        ],
        "scoringStories": [
            {
                "title": "可信评估体系",
                "tag": "Evaluation",
                "detail": "训练、验证和测试节点严格分离，时间型数据采用时间切分，分数口径可复核。",
            },
            {
                "title": "结构特征增益",
                "tag": "Feature",
                "detail": "在原始节点属性基础上引入度数、交易类型、时间窗口和邻居风险统计，使模型能够捕捉团伙化欺诈行为。",
            },
            {
                "title": "统一数据架构",
                "tag": "Data",
                "detail": "同一套数据注册、特征构建、训练评估和可视化流程覆盖图节点分类、表格交易欺诈和 AML 仿真样例。",
            },
            {
                "title": "风险解释能力",
                "tag": "Explainability",
                "detail": "系统展示关键特征、匿名关系子图和风险邻域，使识别结果能够支撑风控复核和团伙线索追踪。",
            },
            {
                "title": "系统交付闭环",
                "tag": "Delivery",
                "detail": "系统包含统一命令入口、指标产物、提交文件、展示面板和流式处理原型，覆盖离线训练到在线演示。",
            },
        ],
        "referenceInsights": [
            {
                "source": "官方基线",
                "good": "提供统一数据加载、训练切分和 GraphSAGE 邻居采样基线，是衡量主链路是否可信的最低参照。",
                "absorbed": "保留官方数据字段和训练索引边界，展示输入结构、切分和验证口径。",
                "gap": "本系统补充风险等级、案件处置和审计记录。",
            },
            {
                "source": "GEARSage",
                "good": "强调边方向、边时间、边类型和邻域衰减，适合捕捉金融图中的关系噪声与风险传播。",
                "absorbed": "126 维特征覆盖方向、类型、时间窗口、一跳邻居和风险邻域统计。",
                "gap": "轻量树模型方案兼顾训练成本、推理效率和可解释性。",
            },
            {
                "source": "TGN 与动态图方案",
                "good": "把交易关系按时间事件处理，强调动态邻居、时间编码和新节点泛化。",
                "absorbed": "交易流回放、微批评分、风险等级输出和一跳溯源摘要接入展示链路。",
                "gap": "本系统将动态交易事件转化为可审计风险事件。",
            },
            {
                "source": "风控调查台项目",
                "good": "真实落地系统不只输出分数，还需要案件队列、阈值策略、人工复核和审计链路。",
                "absorbed": "大屏新增调查控制台、模型版本、阈值策略、处置状态、复核结论和审计记录。",
                "gap": "风险分、建议动作、复核状态和审计日志在同一案件视图中联动展示。",
            },
        ],
        "datasets": datasets,
        "graphSample": _build_graph_sample(),
        "fraudScenarios": _build_fraud_scenarios(),
        "policy": _build_policy_payload(primary_dataset, output_dir),
        "investigation": _build_investigation_payload(output_dir),
        "inferenceFlow": [
            {
                "step": "01",
                "title": "事件与节点接入",
                "body": "读取匿名节点属性、交易边类型、时间戳和训练期已知标签上下文，保持和赛题数据格式一致。",
            },
            {
                "step": "02",
                "title": "图与时间特征展开",
                "body": "构建度数、交易类型计数、时间窗口、邻居聚合和背景节点上下文，不依赖测试标签做任何增强。",
            },
            {
                "step": "03",
                "title": "双树模型融合评分",
                "body": "以 XGBoost 作为主干，LightGBM 作为辅助模型，用轻量融合兼顾稳定性、可解释性和推理效率。",
            },
            {
                "step": "04",
                "title": "风险输出与人工复核",
                "body": "输出风险分、重点触发特征和关联结构线索，方便风控台做团伙追溯和人工复核闭环。",
            },
        ],
        "implementation": [
            {
                "title": "多维特征构建",
                "status": "已完成",
                "detail": "原始节点特征、交易类型统计、时间统计、一跳邻居聚合和无泄漏风险邻域增强进入主训练链路。",
            },
            {
                "title": "评估与提交链路",
                "status": "已完成",
                "detail": "DGraph-Fin、DGraph-Fin2 和多类公开数据均可训练、评估并导出结果文件。",
            },
            {
                "title": "团伙结构与可视化",
                "status": "展示完成",
                "detail": "风险事件联动一跳邻域、交易方向、邻居标签摘要和关系图，支撑团伙线索复核。",
            },
            {
                "title": "仿真环境",
                "status": "展示完成",
                "detail": "AMLSim sample 已接入，DGraph-Fin 交易边也已支持按时间戳抽样回放，并补充渠道、金额和设备指纹模拟字段。",
            },
            {
                "title": "流式识别框架",
                "status": "链路完成",
                "detail": "交易流回放、微批评分、风险等级、建议动作和可审计风险事件文件形成闭环。",
            },
            {
                "title": "性能实测",
                "status": "已完成",
                "detail": "5000 条交易回放实测约 44231 events/s，纯评分吞吐约 127412 nodes/s，平均节点评分延迟约 0.0078 ms。",
            },
            {
                "title": "安全与合规",
                "status": "已完成",
                "detail": "展示数据脱敏、输入边界、风险等级、处置策略和可审计预测记录。",
            },
        ],
        "caveats": [
            {
                "title": "DGraph-Fin2 节点时间字段",
                "body": "节点时间字段与目标标签存在强相关风险，默认训练流程不将其作为直接输入，以保证评估结果可复核。",
            },
            {
                "title": "IEEE 必须按时间切分",
                "body": "交易欺诈识别具有明显时序属性，系统采用基于 TransactionDT 的时间验证，避免随机切分带来的乐观估计。",
            },
            {
                "title": "Elliptic++ 口径",
                "body": "该数据集更适合作为地址级 AML 分类补充基准，展示时不将其绝对分数与图节点反欺诈基准直接比较。",
            },
            {
                "title": "公开结果对比原则",
                "body": "跨数据版本、跨切分策略和跨评估目标的分数不直接横向比较，系统以统一可复核流程呈现结果。",
            },
        ],
        "sources": [
            r"docs\\report\\competition-report.typ",
            r"docs\\runs.md",
            r"data\\DGraphFin\\DGraphFin1\\dgraphfin.npz",
            r"data\\DGraphFin\\DGraphFin2\\dgraphfinv2_edge_timestamp.npy",
            r"data\\ieee-fraud-detection",
            r"data\\amlsim\\sample\\outputs",
            r"output\\dgraph_fin\\metrics\\xgboost_metrics.json",
            r"output\\dgraph_fin2\\metrics\\xgboost_metrics.json",
            r"output\\ieee_cis\\metrics\\xgboost_metrics.json",
            r"output\\elliptic_pp\\metrics\\xgboost_no_label_neighbors_metrics.json",
            r"output\\streaming\\performance_report.md",
            r"output\\streaming\\ring_trace_summary.json",
        ],
    }


def _build_dataset_payloads(output_dir: Path) -> list[dict[str, object]]:
    dgraph_fin_metrics = _read_metrics(output_dir / "dgraph_fin" / "metrics" / "xgboost_metrics.json")
    dgraph_fin2_metrics = _read_metrics(output_dir / "dgraph_fin2" / "metrics" / "xgboost_metrics.json")
    ieee_metrics = _read_metrics(output_dir / "ieee_cis" / "metrics" / "xgboost_metrics.json")
    elliptic_metrics = _read_metrics(output_dir / "elliptic_pp" / "metrics" / "xgboost_no_label_neighbors_metrics.json")
    amlsim_metrics = _read_metrics(output_dir / "amlsim_sample" / "metrics" / "xgboost_metrics.json")

    dgraph_fin_local = _load_dgraph_fin_local_summary()
    dgraph_fin2_local = _load_dgraph_fin2_local_summary()
    ieee_local = _load_ieee_local_summary()
    amlsim_local = _load_amlsim_local_summary()

    return [
        {
            "key": "dgraph_fin",
            "name": "DGraph-Fin",
            "tagline": "官方公开基准",
            "modality": "图节点反欺诈",
            "trustedAuc": dgraph_fin_metrics["valid_auc"],
            "summary": "官方公开图基准，用于展示图特征方案在大规模匿名交易关系网络上的识别能力。",
            "badges": ["公开数据", "图数据", "迁移验证"],
            "metrics": [
                {"label": "节点", "value": dgraph_fin_local["nodes"]},
                {"label": "边", "value": dgraph_fin_local["edges"]},
                {"label": "验证样本", "value": dgraph_fin_metrics["valid_size"]},
                {"label": "特征维度", "value": dgraph_fin_metrics["feature_count"]},
            ],
            "annotations": [
                {"label": "训练样本", "value": f"{dgraph_fin_metrics['train_size']:,}"},
                {"label": "训练正样本占比", "value": format_ratio_value(dgraph_fin_metrics["positive_ratio_train"])},
                {"label": "标签分布", "value": "正类 15,509，正常 1,210,092，背景 2/3 共 2,474,949"},
                {"label": "时间范围", "value": f"edge timestamp {dgraph_fin_local['time_range']}"},
            ],
            "availability": "公开图基准与实验产物完整接入。",
            "trustLine": "核心公开图基准",
            "trustNote": "训练、验证和测试索引严格分离，图结构、时间统计和风险邻域特征均限定在可用输入范围内。",
            "caution": "用于验证图特征方案在大规模交易关系图上的识别表现。",
            "topFeatures": _read_top_features(output_dir / "dgraph_fin" / "figures" / "feature_importance.csv"),
            "profile": _dgraph_fin_profile(dgraph_fin_local),
        },
        {
            "key": "dgraph_fin2",
            "name": "DGraph-Fin2",
            "tagline": "时间增强扩展包",
            "modality": "图时序反欺诈",
            "trustedAuc": dgraph_fin2_metrics["valid_auc"],
            "summary": "DGraph-Fin 的时间增强扩展数据，用于验证系统对时间型图信息的接入和约束能力。",
            "badges": ["公开数据", "图时序", "泄漏已排除"],
            "metrics": [
                {"label": "节点", "value": dgraph_fin_local["nodes"]},
                {"label": "边", "value": dgraph_fin_local["edges"]},
                {"label": "验证样本", "value": dgraph_fin2_metrics["valid_size"]},
                {"label": "特征维度", "value": dgraph_fin2_metrics["feature_count"]},
            ],
            "annotations": [
                {"label": "训练样本", "value": f"{dgraph_fin2_metrics['train_size']:,}"},
                {"label": "训练正样本占比", "value": format_ratio_value(dgraph_fin2_metrics["positive_ratio_train"])},
                {"label": "时间文件", "value": f"node {dgraph_fin2_local['node_timestamp_rows']:,}，edge {dgraph_fin2_local['edge_timestamp_rows']:,}"},
                {"label": "特征策略", "value": "移除节点时间标签，保留图结构与边时间统计"},
            ],
            "availability": "时间扩展包与基础图接入统一训练流程。",
            "trustLine": "时间增强图的可信口径",
            "trustNote": "默认不直接使用存在标签相关风险的节点时间字段，保留边时间统计和结构统计。",
            "caution": "时间增强信息仅在满足评估约束的前提下使用。",
            "topFeatures": _read_top_features(output_dir / "dgraph_fin2" / "figures" / "feature_importance.csv"),
            "profile": _dgraph_fin2_profile(dgraph_fin_local, dgraph_fin2_local),
        },
        {
            "key": "ieee_cis",
            "name": "IEEE-CIS",
            "tagline": "表格欺诈对照集",
            "modality": "表格交易反欺诈",
            "trustedAuc": ieee_metrics["valid_auc"],
            "summary": "公开表格交易欺诈数据，用于展示系统在非图结构金融风控场景下的迁移能力。",
            "badges": ["公开数据", "表格数据", "时间切分"],
            "metrics": [
                {"label": "训练交易", "value": ieee_local["train_transaction_rows"]},
                {"label": "测试交易", "value": ieee_local["test_transaction_rows"]},
                {"label": "验证样本", "value": ieee_metrics["valid_size"]},
                {"label": "特征维度", "value": ieee_metrics["feature_count"]},
            ],
            "annotations": [
                {"label": "身份表行数", "value": f"train {ieee_local['train_identity_rows']:,} / test {ieee_local['test_identity_rows']:,}"},
                {"label": "训练正样本占比", "value": format_ratio_value(ieee_metrics["positive_ratio_train"])},
                {"label": "融合方式", "value": "0.8 XGBoost + 0.2 LightGBM"},
                {"label": "可信口径", "value": "按 TransactionDT 做时间切分"},
            ],
            "availability": "表格交易数据和实验产物已接入。",
            "trustLine": "表格时序对照验证",
            "trustNote": "从随机分层切分切换到时间切分后，分数回落到更可信区间。",
            "caution": "该结果用于跨模态验证，不与图节点分类主任务直接比较。",
            "topFeatures": _read_top_features(output_dir / "ieee_cis" / "figures" / "feature_importance.csv"),
            "profile": _ieee_profile(ieee_local, ieee_metrics),
        },
        {
            "key": "elliptic_pp",
            "name": "Elliptic++",
            "tagline": "公开 AML 图基准",
            "modality": "地址级反洗钱图",
            "trustedAuc": elliptic_metrics["valid_auc"],
            "summary": "公开地址级 AML 图基准，用于补充展示地址关系网络上的风险识别能力。",
            "badges": ["公开数据", "AML 图", "非因果基准"],
            "metrics": [
                {"label": "钱包地址", "value": 822_942},
                {"label": "addr-addr 边", "value": 2_868_964},
                {"label": "验证样本", "value": elliptic_metrics["valid_size"]},
                {"label": "特征维度", "value": elliptic_metrics["feature_count"]},
            ],
            "annotations": [
                {"label": "训练样本", "value": f"{elliptic_metrics['train_size']:,}"},
                {"label": "训练正样本占比", "value": format_ratio_value(elliptic_metrics["positive_ratio_train"])},
                {"label": "时间范围", "value": "49 个 time step"},
                {"label": "验证策略", "value": "未来段验证 + 移除 Time step 直入特征 + 停用伪造边时间戳"},
            ],
            "availability": "地址关系图数据和严格验证指标已接入。",
            "trustLine": "时间验证口径",
            "trustNote": "验证流程移除显式时间字段输入，并使用未来时间段作为验证集。",
            "caution": "该数据集定位为 AML 地址分类补充基准，不作为主任务分数对比依据。",
            "topFeatures": _read_top_features(output_dir / "elliptic_pp" / "figures" / "feature_importance_no_label_neighbors.csv"),
            "profile": _elliptic_profile(elliptic_metrics),
        },
        {
            "key": "amlsim_sample",
            "name": "AMLSim Sample",
            "tagline": "仿真样例",
            "modality": "账户交易反洗钱样例",
            "trustedAuc": amlsim_metrics["valid_auc"],
            "summary": "AMLSim 仿真输出样例，用于展示账户、交易、告警等结构化金融数据的接入方式。",
            "badges": ["本地样例", "CSV", "仿真数据"],
            "metrics": [
                {"label": "账户", "value": amlsim_local["accounts"]},
                {"label": "交易", "value": amlsim_local["transactions"]},
                {"label": "验证样本", "value": amlsim_metrics["valid_size"]},
                {"label": "特征维度", "value": amlsim_metrics["feature_count"]},
            ],
            "annotations": [
                {"label": "训练样本", "value": f"{amlsim_metrics['train_size']:,}"},
                {"label": "训练正样本占比", "value": format_ratio_value(amlsim_metrics["positive_ratio_train"])},
                {"label": "交易类型", "value": amlsim_local["transaction_types"]},
                {"label": "时间范围", "value": amlsim_local["time_range"]},
            ],
            "availability": "AMLSim 样例表、账户标签和交易边已接入。",
            "trustLine": "工程接入样例",
            "trustNote": "样本规模较小，主要用于数据结构演示和链路验证。",
            "caution": "该样例不作为正式效果评测数据。",
            "topFeatures": _read_top_features(output_dir / "amlsim_sample" / "figures" / "feature_importance.csv"),
            "profile": _amlsim_profile(amlsim_local),
        },
        {
            "key": "ibm_aml",
            "name": "IBM Synthetic AML",
            "tagline": "扩展接口",
            "modality": "合成交易反洗钱数据",
            "trustedAuc": None,
            "summary": "合成 AML 数据接入位，用于展示系统对交易级反洗钱数据的扩展接口。",
            "badges": ["扩展接口", "CSV", "合成数据"],
            "metrics": [
                {"label": "本地文件", "value": "扩展接口"},
                {"label": "训练样本", "value": "按数据生成"},
                {"label": "验证样本", "value": "按切分生成"},
                {"label": "特征维度", "value": "按字段生成"},
            ],
            "annotations": [
                {"label": "默认路径", "value": str(APP_CONFIG.dataset_path("ibm_aml"))},
                {"label": "问题类型", "value": "表格或图反洗钱二分类"},
                {"label": "接入状态", "value": "接口注册"},
                {"label": "验证要求", "value": "按时间列切分"},
            ],
            "availability": "扩展接口展示，不纳入公开基准结果。",
            "trustLine": "扩展口径",
            "trustNote": "正式评估需锁定标签列、时间列和训练切分。",
            "caution": "不参与公开基准结果对比。",
            "topFeatures": ["接入正式数据后输出特征重要度。"],
            "profile": _ibm_aml_profile(),
        },
    ]


def _build_graph_sample() -> dict[str, object]:
    npz_path = APP_CONFIG.dataset_path("dgraph_fin") / "dgraphfin.npz"
    if not npz_path.exists():
        return {
            "title": "DGraph-Fin 匿名关系样本",
            "description": "DGraph-Fin 基础图可用于抽取匿名高风险节点的一跳关系结构。",
            "focusNode": {"id": -1},
            "nodes": [],
            "edges": [],
            "metrics": [],
            "annotation": "接入基础图文件后，页面将自动抽取匿名高风险节点的一跳关系结构。",
            "legend": [
                {"label": "欺诈", "color": "#ff7c6b"},
                {"label": "正常", "color": "#8ee0c8"},
                {"label": "背景", "color": "#6f8f97"},
            ],
        }

    arrays = np.load(npz_path)
    y = arrays["y"].reshape(-1).astype(np.int64)
    edge_index = arrays["edge_index"].astype(np.int64)
    edge_type = arrays["edge_type"].reshape(-1).astype(np.int64)
    edge_timestamp = arrays["edge_timestamp"].reshape(-1).astype(np.int64)

    fraud_nodes = np.flatnonzero(y == 1)
    node_ids, degree_counts = np.unique(edge_index.reshape(-1), return_counts=True)
    degree_map = dict(zip(node_ids.tolist(), degree_counts.tolist()))
    focus_node = max(fraud_nodes.tolist(), key=lambda node: degree_map.get(node, 0))

    in_mask = edge_index[:, 1] == focus_node
    out_mask = edge_index[:, 0] == focus_node
    incident_mask = in_mask | out_mask
    incident_edges = np.flatnonzero(incident_mask)

    neighbor_scores: dict[int, int] = {}
    for edge_idx in incident_edges:
        src, dst = edge_index[edge_idx]
        neighbor = int(dst if src == focus_node else src)
        neighbor_scores[neighbor] = neighbor_scores.get(neighbor, 0) + 1

    selected_neighbors = [
        node for node, _ in sorted(neighbor_scores.items(), key=lambda item: (-item[1], item[0]))[:14]
    ]
    selected_nodes = [focus_node] + selected_neighbors
    selected_set = set(selected_nodes)

    nodes = [
        {
            "id": int(node),
            "label": int(y[node]),
            "degree": int(degree_map.get(int(node), 0)),
        }
        for node in selected_nodes
    ]

    edges = []
    for edge_idx in incident_edges:
        src, dst = edge_index[edge_idx]
        src_id = int(src)
        dst_id = int(dst)
        if src_id in selected_set and dst_id in selected_set:
            edges.append(
                {
                    "source": src_id,
                    "target": dst_id,
                    "type": int(edge_type[edge_idx]),
                    "timestamp": int(edge_timestamp[edge_idx]),
                }
            )

    incident_timestamps = edge_timestamp[incident_mask]
    incident_types = edge_type[incident_mask]
    neighbor_labels = y[np.unique(edge_index[incident_mask].reshape(-1))]

    return {
        "title": "DGraph-Fin 匿名高风险节点一跳子图",
        "description": (
            "该子图来自本地 DGraph-Fin 中一个高风险节点的一跳关系网络，用于展示交易方向、关系类型和邻域结构对风险识别的贡献。"
        ),
        "focusNode": {"id": int(focus_node)},
        "nodes": nodes,
        "edges": edges,
        "metrics": [
            {"label": "入度", "value": str(int(in_mask.sum()))},
            {"label": "出度", "value": str(int(out_mask.sum()))},
            {"label": "活跃时间窗", "value": f"{int(incident_timestamps.min())}-{int(incident_timestamps.max())}"},
            {"label": "主导交易类型", "value": f"type {int(np.bincount(incident_types).argmax())}"},
        ],
        "annotation": (
            f"该节点在完整图中共有 {int(in_mask.sum())} 条入边、0 条出边，入边集中来自同一种交易类型。"
            " 邻域内同时包含正常节点和背景节点，说明模型需要结合单点画像、交易方向和邻域统计进行综合判断。"
        ),
        "legend": [
            {"label": "欺诈节点", "color": "#ff7c6b"},
            {"label": "正常节点", "color": "#8ee0c8"},
            {"label": "背景标签 2", "color": "#f2b35d"},
            {"label": "背景标签 3", "color": "#6f8f97"},
        ],
        "neighborLabelSummary": {
            "fraud": int(np.sum(neighbor_labels == 1)),
            "normal": int(np.sum(neighbor_labels == 0)),
            "context2": int(np.sum(neighbor_labels == 2)),
            "context3": int(np.sum(neighbor_labels == 3)),
        },
    }


def _build_fraud_scenarios() -> list[dict[str, object]]:
    return [
        {
            "name": "循环转账",
            "riskLevel": "critical",
            "pattern": "账户 A、B、C 在短时间内形成闭环转账，金额逐步拆小，最终回到起点或同一控制账户。",
            "signal": "闭环路径、时间间隔短、交易类型集中、同设备或同渠道重复出现。",
            "modelResponse": "提高焦点节点风险分，并在溯源视图中暴露闭环邻居和主导交易类型。",
            "generatedCase": {
                "event": "SIM-RING-001",
                "riskScore": 0.94,
                "decision": "critical / freeze_and_manual_review",
                "summary": "生成 4 个账户、4 条交易边，识别为闭环链路。",
            },
            "nodes": ["A", "B", "C", "D"],
            "edges": [["A", "B"], ["B", "C"], ["C", "A"], ["C", "D"]],
            "stats": [
                {"label": "链路长度", "value": "3-4 跳"},
                {"label": "处置建议", "value": "冻结拦截"},
            ],
        },
        {
            "name": "分散汇集",
            "riskLevel": "high",
            "pattern": "多个低风险账户向同一收款账户汇集小额交易，单笔看似正常，聚合后形成异常入度峰值。",
            "signal": "入度突增、金额分散、时间窗口集中、收款节点邻域中背景账户比例较高。",
            "modelResponse": "通过入度、交易类型统计和邻域聚合特征提升收款账户风险。",
            "generatedCase": {
                "event": "SIM-FANIN-002",
                "riskScore": 0.78,
                "decision": "high / manual_review",
                "summary": "生成 4 个付款账户汇入同一收款账户，识别为汇集异常。",
            },
            "nodes": ["P1", "P2", "P3", "P4", "M"],
            "edges": [["P1", "M"], ["P2", "M"], ["P3", "M"], ["P4", "M"]],
            "stats": [
                {"label": "主风险点", "value": "收款账户"},
                {"label": "处置建议", "value": "人工复核"},
            ],
        },
        {
            "name": "集中转出",
            "riskLevel": "high",
            "pattern": "一个高风险账户在短时间内向多个新账户或背景账户转出资金，用于分散风险和逃避追踪。",
            "signal": "出度突增、交易时间跨度短、目标账户历史稀疏、主导交易类型占比高。",
            "modelResponse": "通过出度、时间跨度和主导交易类型特征识别扩散式风险。",
            "generatedCase": {
                "event": "SIM-FANOUT-003",
                "riskScore": 0.81,
                "decision": "high / manual_review",
                "summary": "生成 1 个付款账户转向 4 个新账户，识别为集中转出。",
            },
            "nodes": ["S", "T1", "T2", "T3", "T4"],
            "edges": [["S", "T1"], ["S", "T2"], ["S", "T3"], ["S", "T4"]],
            "stats": [
                {"label": "主风险点", "value": "付款账户"},
                {"label": "处置建议", "value": "二次验证"},
            ],
        },
        {
            "name": "账户团伙",
            "riskLevel": "critical",
            "pattern": "多个账户形成高密度交易子图，部分账户已知风险，其他账户通过邻域风险传播暴露嫌疑。",
            "signal": "团伙内部交易密集、已知欺诈邻居、背景节点混杂、风险等级在子图内传播。",
            "modelResponse": "无泄漏风险邻域统计捕捉已知风险邻居，并为人工复核提供团伙线索。",
            "generatedCase": {
                "event": "SIM-GROUP-004",
                "riskScore": 0.91,
                "decision": "critical / freeze_and_manual_review",
                "summary": "生成 5 个账户的高密度子图，识别为团伙协作风险。",
            },
            "nodes": ["G1", "G2", "G3", "G4", "G5"],
            "edges": [["G1", "G2"], ["G2", "G3"], ["G3", "G4"], ["G4", "G1"], ["G2", "G5"]],
            "stats": [
                {"label": "结构特征", "value": "高密度子图"},
                {"label": "处置建议", "value": "批量复核"},
            ],
        },
    ]


def _build_policy_payload(primary_dataset: dict[str, object], output_dir: Path) -> dict[str, object]:
    risk_path = output_dir / "streaming" / "risk_events.csv"
    hit_counts: dict[str, int] = {}
    if risk_path.exists():
        risk_frame = pd.read_csv(risk_path, usecols=["risk_level"])
        hit_counts = {str(key): int(value) for key, value in risk_frame["risk_level"].value_counts().items()}

    risk_levels = [
        {
            "level": item.level,
            "threshold": item.threshold,
            "action": item.action,
            "hitCount": hit_counts.get(item.level, 0),
        }
        for item in APP_CONFIG.risk_levels
    ]
    return {
        "model": {
            "version": f"{primary_dataset['key']}-xgb-lgb-v3",
            "dataset": primary_dataset["name"],
            "auc": primary_dataset["trustedAuc"],
            "featureCount": primary_dataset["metrics"][3]["value"],
            "updatedAt": datetime.now().strftime("%Y-%m-%d"),
        },
        "thresholds": risk_levels,
        "batch": {
            "input": "output/streaming/transaction_stream_sample.csv",
            "output": "output/streaming/risk_events.csv",
            "audit": "output/streaming/ring_trace_summary.json",
        },
    }


def _build_investigation_payload(output_dir: Path) -> dict[str, object]:
    store_path = default_sqlite_path(output_dir)
    if store_path.exists():
        store = RiskEventStore(f"sqlite:///{store_path.as_posix()}")
        summary = store.summary()
        return {
            "available": True,
            "summary": {
                "caseCount": summary.event_count,
                "criticalCount": summary.critical_count,
                "highCount": summary.high_count,
                "mediumCount": summary.medium_count,
                "lowCount": summary.low_count,
                "auditCount": min(summary.event_count, 8),
            },
            "cases": store.load_cases(limit=8),
        }

    risk_path = output_dir / "streaming" / "risk_events.csv"
    trace_path = output_dir / "streaming" / "ring_trace_summary.json"
    if not risk_path.exists() or not trace_path.exists():
        return {
            "available": False,
            "summary": {
                "caseCount": 0,
                "criticalCount": 0,
                "highCount": 0,
                "auditCount": 0,
            },
            "cases": [],
        }

    risk_frame = pd.read_csv(risk_path)
    trace_data = json.loads(trace_path.read_text(encoding="utf-8"))
    traces_by_event = {int(item["event_id"]): item for item in trace_data.get("traces", [])}
    selected = risk_frame.sort_values("risk_score", ascending=False).head(8).copy()
    cases: list[dict[str, object]] = []
    for index, row in enumerate(selected.itertuples(index=False), start=1):
        event_id = int(row.event_id)
        trace = traces_by_event.get(event_id, {})
        status = _case_status(row.risk_level)
        review = _case_review(row.risk_level)
        cases.append(
            {
                "caseId": f"CASE-{event_id:05d}",
                "eventId": event_id,
                "timestamp": int(row.timestamp),
                "riskScore": float(row.risk_score),
                "riskLevel": str(row.risk_level),
                "action": str(row.action),
                "status": status,
                "review": review,
                "focusNode": int(row.focus_node),
                "srcNode": int(row.src_node),
                "dstNode": int(row.dst_node),
                "channel": str(row.channel),
                "amount": float(row.amount),
                "explanation": str(row.explanation),
                "trace": {
                    "neighborCount": int(trace.get("neighbor_count", 0)),
                    "fraudNeighborCount": int(trace.get("fraud_neighbor_count", 0)),
                    "normalNeighborCount": int(trace.get("normal_neighbor_count", 0)),
                    "backgroundNeighborCount": int(trace.get("background_neighbor_count", 0)),
                    "incidentEdgeCount": int(trace.get("incident_edge_count", 0)),
                    "dominantEdgeType": int(trace.get("dominant_edge_type", row.edge_type)),
                    "dominantEdgeTypeShare": float(trace.get("dominant_edge_type_share", 0.0)),
                    "timeSpan": int(trace.get("time_span", 0)),
                },
                "audit": [
                    f"事件 {event_id} 进入实时评分队列，渠道 {row.channel}，金额 {float(row.amount):.2f}",
                    f"模型输出 {float(row.risk_score):.4f}，风险等级 {row.risk_level}，建议动作 {row.action}",
                    f"复核结论：{review}",
                ],
            }
        )

    return {
        "available": True,
        "summary": {
            "caseCount": int(risk_frame.shape[0]),
            "criticalCount": int((risk_frame["risk_level"] == "critical").sum()),
            "highCount": int((risk_frame["risk_level"] == "high").sum()),
            "auditCount": len(cases),
        },
        "cases": cases,
    }


def _case_status(risk_level: str) -> str:
    if risk_level == "critical":
        return "冻结待复核"
    if risk_level == "high":
        return "人工复核中"
    if risk_level == "medium":
        return "二次验证"
    return "自动放行"


def _case_review(risk_level: str) -> str:
    if risk_level == "critical":
        return "建议立即冻结并核查同邻域账户"
    if risk_level == "high":
        return "建议人工复核交易链路和设备指纹"
    if risk_level == "medium":
        return "建议触发二次验证后再放行"
    return "暂未发现强风险信号"


def _load_dgraph_fin_local_summary() -> dict[str, object]:
    npz_path = APP_CONFIG.dataset_path("dgraph_fin") / "dgraphfin.npz"
    if not npz_path.exists():
        return {
            "available": False,
            "nodes": 3_700_550,
            "edges": 4_300_999,
            "time_range": "1-821",
            "label_counts": {0: 1_210_092, 1: 15_509, 2: 1_620_851, 3: 854_098},
            "split_counts": {"train": 857_899, "valid": 183_862, "test": 183_840},
            "edge_type_counts": [],
            "sample": {"columns": [], "rows": []},
        }

    arrays = np.load(npz_path)
    y = arrays["y"].reshape(-1).astype(np.int64)
    labels, label_counts = np.unique(y, return_counts=True)
    edge_timestamp = arrays["edge_timestamp"].reshape(-1).astype(np.int64)
    edge_type = arrays["edge_type"].reshape(-1).astype(np.int64)
    types, type_counts = np.unique(edge_type, return_counts=True)
    sample_nodes = np.array([arrays["train_mask"][0], arrays["valid_mask"][0], arrays["test_mask"][0]], dtype=np.int64)
    sample_rows = []
    for node in sample_nodes.tolist():
        feature_head = arrays["x"][node, :5].astype(float).tolist()
        sample_rows.append(
            {
                "node_id": int(node),
                "label": int(y[node]),
                "feat_0": _format_sample_value(feature_head[0]),
                "feat_1": _format_sample_value(feature_head[1]),
                "feat_2": _format_sample_value(feature_head[2]),
                "feat_3": _format_sample_value(feature_head[3]),
                "feat_4": _format_sample_value(feature_head[4]),
            }
        )
    return {
        "available": True,
        "nodes": int(arrays["x"].shape[0]),
        "edges": int(arrays["edge_index"].shape[0]),
        "time_range": f"{int(edge_timestamp.min())}-{int(edge_timestamp.max())}",
        "feature_count": int(arrays["x"].shape[1]),
        "label_counts": {int(label): int(count) for label, count in zip(labels, label_counts)},
        "split_counts": {
            "train": int(arrays["train_mask"].reshape(-1).shape[0]),
            "valid": int(arrays["valid_mask"].reshape(-1).shape[0]),
            "test": int(arrays["test_mask"].reshape(-1).shape[0]),
        },
        "edge_type_counts": [
            {"label": f"type {int(edge_value)}", "value": int(count)}
            for edge_value, count in zip(types, type_counts)
        ],
        "sample": {
            "columns": ["node_id", "label", "feat_0", "feat_1", "feat_2", "feat_3", "feat_4"],
            "rows": sample_rows,
        },
    }


def _load_dgraph_fin2_local_summary() -> dict[str, object]:
    dataset_dir = APP_CONFIG.dataset_path("dgraph_fin2")
    edge_ts_path = dataset_dir / "dgraphfinv2_edge_timestamp.npy"
    node_ts_path = dataset_dir / "dgraphfinv2_node_timestamp.npy"
    if not edge_ts_path.exists() or not node_ts_path.exists():
        return {
            "available": False,
            "edge_timestamp_rows": 4_300_999,
            "node_timestamp_rows": 3_700_550,
            "edge_time_range": "未知",
            "node_time_range": "未知",
            "node_timestamp_nonzero": 0,
        }

    edge_ts = np.load(edge_ts_path, allow_pickle=True).reshape(-1).astype(np.int64)
    node_ts = np.load(node_ts_path, allow_pickle=True).reshape(-1).astype(np.int64)
    missing_sentinel = int(np.iinfo(np.int32).min)
    valid_node_ts = node_ts[node_ts != missing_sentinel]
    return {
        "available": True,
        "edge_timestamp_rows": int(edge_ts.shape[0]),
        "node_timestamp_rows": int(node_ts.shape[0]),
        "edge_time_range": f"{int(edge_ts.min())}-{int(edge_ts.max())}",
        "node_time_range": f"{int(valid_node_ts.min())}-{int(valid_node_ts.max())}" if valid_node_ts.size else "无有效时间",
        "node_timestamp_nonzero": int(valid_node_ts.shape[0]),
        "node_timestamp_missing": int(node_ts.shape[0] - valid_node_ts.shape[0]),
    }


def _load_ieee_local_summary() -> dict[str, int]:
    dataset_dir_candidates = [
        APP_CONFIG.dataset_path("ieee_cis"),
    ]
    dataset_dir = next((path for path in dataset_dir_candidates if path.exists()), None)
    if dataset_dir is None:
        return {
            "available": False,
            "train_transaction_rows": 590_540,
            "test_transaction_rows": 506_691,
            "train_identity_rows": 144_233,
            "test_identity_rows": 141_907,
            "train_positive": 20_663,
            "train_negative": 569_877,
            "transaction_time_range": "未知",
            "schema": [],
            "sample": {"columns": [], "rows": []},
        }

    train_preview = pd.read_csv(
        dataset_dir / "train_transaction.csv",
        usecols=["TransactionID", "isFraud", "TransactionDT", "TransactionAmt", "ProductCD", "card1"],
        nrows=3,
    )
    sample_columns = ["TransactionID", "isFraud", "TransactionDT", "TransactionAmt", "ProductCD", "card1"]
    sample_rows = _frame_sample_records(train_preview, sample_columns)
    return {
        "available": True,
        "train_transaction_rows": 590_540,
        "test_transaction_rows": 506_691,
        "train_identity_rows": 144_233,
        "test_identity_rows": 141_907,
        "train_positive": 20_663,
        "train_negative": 569_877,
        "transaction_time_range": "86400-15811131",
        "schema": [
            {"name": "train_transaction", "detail": "交易主表 394 列"},
            {"name": "train_identity", "detail": "身份扩展表 41 列"},
            {"name": "test_transaction", "detail": "测试交易主表"},
            {"name": "sample_submission", "detail": "提交模板"},
        ],
        "sample": {"columns": sample_columns, "rows": sample_rows},
    }


def _load_amlsim_local_summary() -> dict[str, object]:
    sample_dir = APP_CONFIG.dataset_path("amlsim_sample")
    accounts_path = sample_dir / "accounts.csv"
    tx_path = sample_dir / "tx.csv"
    if not accounts_path.exists() or not tx_path.exists():
        return {
            "available": False,
            "accounts": 0,
            "transactions": 0,
            "fraud_accounts": 0,
            "normal_accounts": 0,
            "transaction_types": "未知",
            "time_range": "未知",
            "account_sample": {"columns": [], "rows": []},
        }

    accounts = pd.read_csv(accounts_path)
    tx = pd.read_csv(tx_path)
    tx_types = sorted(tx["TXN_SOURCE_TYPE_CODE"].astype(str).unique().tolist())
    return {
        "available": True,
        "accounts": int(accounts.shape[0]),
        "transactions": int(tx.shape[0]),
        "fraud_accounts": int(accounts["isFraud"].astype(str).str.lower().eq("true").sum()),
        "normal_accounts": int(accounts["isFraud"].astype(str).str.lower().eq("false").sum()),
        "transaction_types": ", ".join(tx_types),
        "time_range": f"{int(tx['start'].min())}-{int(tx['start'].max())}",
        "account_sample": {
            "columns": ["ACCOUNT_ID", "init_balance", "business", "suspicious", "isFraud", "modelID"],
            "rows": _frame_sample_records(
                accounts,
                ["ACCOUNT_ID", "init_balance", "business", "suspicious", "isFraud", "modelID"],
                row_count=4,
            ),
        },
    }


def _format_sample_value(value: object) -> object:
    if pd.isna(value):
        return ""
    if isinstance(value, (np.integer, int)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return f"{float(value):.4g}"
    return str(value)


def _json_safe(value: object) -> object:
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, np.ndarray):
        return _json_safe(value.tolist())
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        number = float(value)
        if not np.isfinite(number):
            return None
        return number
    return value


def _frame_sample_records(frame: pd.DataFrame, columns: list[str], row_count: int = 3) -> list[dict[str, object]]:
    available_columns = [column for column in columns if column in frame.columns]
    rows: list[dict[str, object]] = []
    for record in frame[available_columns].head(row_count).to_dict(orient="records"):
        rows.append({column: _format_sample_value(record.get(column)) for column in available_columns})
    return rows


def _count_csv_rows(path: Path) -> int:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return max(0, sum(1 for _ in handle) - 1)


def _bars_from_counts(items: list[tuple[str, int]], colors: list[str] | None = None) -> list[dict[str, object]]:
    palette = colors or ["#8ee0c8", "#ff7c6b", "#f2b35d", "#6f8f97", "#9aa8ff", "#d5dee0"]
    return [
        {"label": label, "value": int(value), "color": palette[idx % len(palette)]}
        for idx, (label, value) in enumerate(items)
    ]


def _dgraph_fin_profile(summary: dict[str, object]) -> dict[str, object]:
    label_counts = summary["label_counts"]
    split_counts = summary["split_counts"]
    return {
        "distributionTitle": "节点标签",
        "distribution": _bars_from_counts(
            [
                ("正常 0", int(label_counts.get(0, 0))),
                ("欺诈 1", int(label_counts.get(1, 0))),
                ("背景 2", int(label_counts.get(2, 0))),
                ("背景 3", int(label_counts.get(3, 0))),
            ],
            ["#8ee0c8", "#ff7c6b", "#f2b35d", "#6f8f97"],
        ),
        "splitTitle": "官方切分",
        "splits": _bars_from_counts(
            [
                ("train_mask", int(split_counts["train"])),
                ("valid_mask", int(split_counts["valid"])),
                ("test_mask", int(split_counts["test"])),
            ],
            ["#f2b35d", "#8ee0c8", "#9aa8ff"],
        ),
        "schema": [
            {"name": "x", "detail": f"{summary['nodes']:,} x {summary.get('feature_count', 17)}"},
            {"name": "y", "detail": "4 类节点标签"},
            {"name": "edge_index", "detail": f"{summary['edges']:,} 条边"},
            {"name": "edge_type", "detail": "1 到 11"},
            {"name": "edge_timestamp", "detail": str(summary["time_range"])},
            {"name": "mask", "detail": "训练/验证/测试索引"},
        ],
        "sampleTitle": "节点样本",
        "sample": summary["sample"],
    }


def _dgraph_fin2_profile(base_summary: dict[str, object], time_summary: dict[str, object]) -> dict[str, object]:
    profile = _dgraph_fin_profile(base_summary)
    profile["distributionTitle"] = "时间文件规模"
    profile["distribution"] = _bars_from_counts(
        [
            ("边时间戳", int(time_summary["edge_timestamp_rows"])),
            ("节点时间戳", int(time_summary["node_timestamp_rows"])),
            ("有效节点时间", int(time_summary["node_timestamp_nonzero"])),
            ("缺失占位", int(time_summary.get("node_timestamp_missing", 0))),
        ],
        ["#8ee0c8", "#f2b35d", "#ff7c6b", "#6f8f97"],
    )
    profile["schema"] = profile["schema"] + [
        {"name": "v2_edge_timestamp", "detail": str(time_summary["edge_time_range"])},
        {"name": "v2_node_timestamp", "detail": "默认不进特征"},
    ]
    profile["sampleTitle"] = "时间增强字段"
    profile["sample"] = {
        "columns": ["字段", "范围", "默认处理"],
        "rows": [
            {"字段": "edge_timestamp", "范围": time_summary["edge_time_range"], "默认处理": "用于边时间统计"},
            {"字段": "node_timestamp", "范围": time_summary["node_time_range"], "默认处理": "默认排除"},
        ],
    }
    return profile


def _ieee_profile(summary: dict[str, object], metrics: dict[str, object]) -> dict[str, object]:
    return {
        "distributionTitle": "训练标签",
        "distribution": _bars_from_counts(
            [
                ("正常交易", int(summary["train_negative"])),
                ("欺诈交易", int(summary["train_positive"])),
            ],
            ["#8ee0c8", "#ff7c6b"],
        ),
        "splitTitle": "时间切分",
        "splits": _bars_from_counts(
            [
                ("训练段", int(metrics["train_size"])),
                ("验证段", int(metrics["valid_size"])),
                ("测试交易", int(summary["test_transaction_rows"])),
            ],
            ["#f2b35d", "#8ee0c8", "#9aa8ff"],
        ),
        "schema": summary["schema"],
        "sampleTitle": "交易样本",
        "sample": summary["sample"],
    }


def _elliptic_profile(metrics: dict[str, object]) -> dict[str, object]:
    return {
        "distributionTitle": "训练切分",
        "distribution": _bars_from_counts(
            [
                ("训练节点", int(metrics["train_size"])),
                ("验证节点", int(metrics["valid_size"])),
            ],
            ["#f2b35d", "#8ee0c8"],
        ),
        "splitTitle": "公开统计",
        "splits": _bars_from_counts(
            [
                ("钱包地址", 822_942),
                ("地址关系边", 2_868_964),
                ("时间步", 49),
            ],
            ["#8ee0c8", "#f2b35d", "#9aa8ff"],
        ),
        "schema": [
            {"name": "wallets_features", "detail": "公开钱包特征表"},
            {"name": "wallets_classes", "detail": "地址标签表"},
            {"name": "AddrAddr_edgelist", "detail": "地址关系边表"},
            {"name": "notebooks", "detail": "公开分析笔记本"},
        ],
        "sampleTitle": "数据状态",
        "sample": {
            "columns": ["文件", "状态"],
            "rows": [
                {"文件": "Actors Dataset", "状态": "公开分析资料可用"},
                {"文件": "Transactions Dataset", "状态": "公开分析资料可用"},
                {"文件": "模型产物", "状态": "已生成验证指标"},
            ],
        },
    }


def _amlsim_profile(summary: dict[str, object]) -> dict[str, object]:
    return {
        "distributionTitle": "账户标签",
        "distribution": _bars_from_counts(
            [
                ("正常账户", int(summary["normal_accounts"])),
                ("欺诈账户", int(summary["fraud_accounts"])),
            ],
            ["#8ee0c8", "#ff7c6b"],
        ),
        "splitTitle": "样例表规模",
        "splits": _bars_from_counts(
            [
                ("accounts.csv", int(summary["accounts"])),
                ("tx.csv", int(summary["transactions"])),
                ("alerts.csv", 2),
                ("cash_tx.csv", 48),
            ],
            ["#f2b35d", "#8ee0c8", "#ff7c6b", "#9aa8ff"],
        ),
        "schema": [
            {"name": "accounts", "detail": "账户属性和标签"},
            {"name": "tx", "detail": "账户间交易边"},
            {"name": "alerts", "detail": "告警样例"},
            {"name": "cash_tx", "detail": "现金交易样例"},
        ],
        "sampleTitle": "账户样本",
        "sample": summary["account_sample"],
    }


def _ibm_aml_profile() -> dict[str, object]:
    return {
        "distributionTitle": "接口状态",
        "distribution": _bars_from_counts(
            [
                ("接口注册", 1),
                ("数据文件", 0),
                ("验证指标", 0),
            ],
            ["#f2b35d", "#6f8f97", "#6f8f97"],
        ),
        "splitTitle": "扩展产物",
        "splits": _bars_from_counts(
            [
                ("接口目录", 1),
                ("指标文件", 0),
                ("提交文件", 0),
            ],
            ["#f2b35d", "#6f8f97", "#6f8f97"],
        ),
        "schema": [
            {"name": "transactions", "detail": "交易流水表"},
            {"name": "labels", "detail": "账户或交易标签"},
            {"name": "time column", "detail": "时间切分字段"},
        ],
        "sampleTitle": "扩展要求",
        "sample": {
            "columns": ["项目", "要求"],
            "rows": [
                {"项目": "原始数据", "要求": "CSV 交易流水"},
                {"项目": "切分策略", "要求": "优先按时间设计"},
                {"项目": "展示方式", "要求": "字段预览和指标复核"},
            ],
        },
    }


def _read_metrics(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_top_features(path: Path, top_k: int = 5) -> list[str]:
    rows: list[str] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for idx, row in enumerate(reader):
            if idx >= top_k:
                break
            rows.append(f"{row['feature']} | importance {float(row['importance']):.4f}")
    return rows


def format_ratio_value(value: float) -> str:
    return f"{value * 100:.2f}%"
