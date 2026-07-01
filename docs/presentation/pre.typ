#import "@preview/touying:0.6.1": *
#import "@preview/numbly:0.1.0": numbly
#import "template/theme.typ": *
#import "template/components.typ": *

#show: deck-theme((
  title: [智鉴流盾],
  subtitle: [面向仿真交易流的实时金融反诈识别与动态图溯源系统],
  author: [方向一 #h(0.5em) 欺诈交易智能识别],
  date: [2026-06-03],
  institution: [],
))

#set page(fill: paper)
#set text(font: ("Libertinus Serif", "KaiTi"), fill: slate)
#set heading(numbering: numbly("{1}.", default: "1.1"))
#show heading: set text(font: ("STZhongsong", "KaiTi", "Libertinus Serif"), weight: "semibold")
#show strong: set text(font: ("STZhongsong", "KaiTi", "Libertinus Serif"), weight: "semibold")
#show figure.caption: set text(size: 14pt)
#set list(marker: move(dy: -0.02em, circle(radius: 2.05pt, fill: forest-main)), indent: 0.9em, body-indent: 0.95em)

#let full-figure(path) = {
  v(-0.15em)
  align(center + horizon)[#image(path, height: 330pt)]
}

#title-slide()

= 项目定位

#slide(title: [作品信息])[
  #grid(
    columns: (1fr, 1fr),
    gutter: 20pt,
    [
      #insight-box(title: [任务信息])[
        - 赛题：金融反诈智能守护
        - 方向：方向一 欺诈交易智能识别
        - 场景：跨时段、跨渠道交易风险识别
      ]
    ],
    [
      #accent-box(title: [作品信息])[
        - 项目：智鉴流盾金融反诈智能守护
        - 形态：模型、报告、可视化面板和流式原型
        - 输出：风险分数、风险等级和溯源摘要
      ]
    ],
  )
  #v(1em)
  #block(
    width: 100%,
    inset: 12pt,
    radius: 14pt,
    fill: forest-soft,
    stroke: 0.6pt + forest-main.lighten(35%),
  )[
    #set text(fill: slate, size: 13pt)
    作品围绕方向一构建欺诈交易识别模型、实时风险判定链路和动态图溯源能力。
  ]
]

#slide(title: [项目定位])[
  #grid(
    columns: (1.05fr, 0.95fr),
    gutter: 20pt,
    [
      #insight-box(title: [作品边界])[
        本方案聚焦赛道一的交易反欺诈识别，不泛化为全类型反诈平台。

        当前作品完成三类核心能力：

        - 可复现的主识别链路
        - 可信的离线评测口径
        - 可演示的工程闭环
      ]
      #v(0.7em)
      #accent-box(title: [问题特征])[
        欺诈交易不是单点异常，而是时间行为、关系结构与风险传播共同作用。本方案围绕这三类信息构建识别闭环。
      ]
    ],
    [
      #grid(
        columns: (1fr, 1fr),
        gutter: 10pt,
        [
          #stat-card([DGraph-Fin AUC], [0.828120], note: [公开图基准验证])
        ],
        [
          #stat-card([已接入数据集], [5+], note: [DGraph-Fin、Fin2、IEEE-CIS、Elliptic++、AMLSim], fill: forest-soft)
        ],
        [
          #grid.cell(colspan: 2)[
            #stat-card([交付形态], [模型 + 报告 + 面板], note: [CLI、Typst、Dashboard], fill: amber.lighten(82%), accent: amber.darken(15%))
          ]
        ],
      )
    ],
  )
]

#slide(title: [赛道一聚焦点])[
  #grid(
    columns: (1fr, 1fr),
    gutter: 18pt,
    [
      #insight-box(title: [识别主线])[
        - 交易关系与时间信息建模
        - 结构、时间和风险传播特征融合
        - 模型输出风险分数与风险等级
        - 评测口径保持可复核
      ]
    ],
    [
      #accent-box(title: [方案边界])[
        - 聚焦方向一欺诈交易识别
        - 图分析用于团伙链路挖掘
        - 在线系统形成实时闭环
        - 公开数据结果按当前可复现口径呈现
      ]
    ],
  )
  #v(0.8em)
  #block(
    width: 100%,
    inset: 12pt,
    radius: 14pt,
    fill: forest-soft,
    stroke: 0.6pt + forest-main.lighten(35%),
  )[
    #set text(fill: forest-deep, weight: "semibold", size: 14pt)
    方案核心是围绕欺诈交易识别形成可复现、可解释、可扩展的主链路。
  ]
]

#slide(title: [识别方案主链路])[
  #grid(
    columns: (1fr, 1fr, 1fr, 1fr),
    gutter: 12pt,
    [
      #stat-card([图输入], [370 万节点], note: [17 维节点特征 + 430 万交易边], fill: paper)
    ],
    [
      #stat-card([特征], [126 维], note: [结构、时间、邻居、风险邻域], fill: paper)
    ],
    [
      #stat-card([主模型], [XGBoost], note: [LightGBM 轻量辅助融合], fill: paper)
    ],
    [
      #stat-card([输出], [AUC + 提交], note: [支持实验记录与展示], fill: paper)
    ],
  )
  #v(0.8em)
  #insight-box(title: [设计原则])[
    - 优先保证公开图基准上的识别效果与可复现性
    - 增强过程只依赖训练折已知标签
    - 优先选择稳定、高效、可解释的树模型，不把复杂 GNN 作为第一交付物
    - 流式处理和在线部署放在第二阶段扩展
  ]
]

= 系统架构

#slide(title: [实时反诈平台图形摘要])[
  #full-figure("../report/figures/sci-graphical-abstract.svg")
]

#slide(title: [评分点对应的技术证据])[
  #full-figure("../report/figures/rubric-evidence-matrix.svg")
]

#slide(title: [实时反诈平台总体架构])[
  #full-figure("../online-deployment/figures/realtime-antifraud-platform-preview-1.png")
]

#slide(title: [技术框架与组件选型])[
  #full-figure("../report/figures/technology-framework.svg")
]

#slide(title: [多维特征融合与风险评分])[
  #full-figure("../report/figures/feature-fusion-scoring.svg")
]

#slide(title: [混合云部署与安全边界])[
  #full-figure("../report/figures/hybrid-cloud-security.svg")
]

= 模型评估

#slide(title: [多数据集表现良好])[
  #grid(
    columns: (1fr, 1fr, 1fr, 1fr),
    gutter: 12pt,
    [
      #stat-card([DGraph-Fin], [0.828120], note: [公开图基准], fill: paper)
    ],
    [
      #stat-card([DGraph-Fin2], [0.827919], note: [移除节点时间标签], fill: forest-soft)
    ],
    [
      #stat-card([IEEE-CIS], [0.914582], note: [时间切分验证], fill: amber.lighten(82%), accent: amber.darken(15%))
    ],
    [
      #stat-card([Elliptic++], [0.926556], note: [严格复核口径], fill: paper)
    ],
    [
      #grid.cell(colspan: 3)[
        #insight-box(title: [结果含义])[
          #set text(size: 12.5pt)
          - 覆盖图交易、时间增强图、表格交易和反洗钱图等多种数据形态
          - 多个公开数据集的 AUC 均处于良好水平，且不直接使用存在泄漏风险的字段
        ]
      ]
    ],
    [
      #accent-box(title: [一句话总结])[
        结果链体现的是从单一图基准走向多数据口径复核，而不是只追求单个离线分数。
      ]
    ],
  )
]

#slide(title: [可信性与主动反泄漏])[
  #table(
    columns: (1.2fr, 0.8fr, 2.2fr),
    inset: 8pt,
    stroke: 0.4pt + forest-main.lighten(45%),
    fill: (x, y) => if y == 0 { forest-soft } else { paper },
    [数据集], [可信结果], [主动排查与修正],
    [DGraph-Fin2], [0.827919], [移除会直接暴露正类身份的节点时间标签，不保留虚高结果],
    [IEEE-CIS], [0.914582], [从随机切分改为基于 TransactionDT 的时间切分],
    [Elliptic++], [0.926556], [移除 Time step 直入特征，停用伪造边时间戳，恢复未来段验证],
  )
  #v(0.7em)
  #accent-box(title: [可信性态度])[
    可信性是本方案的重要能力。结果以可解释、可复核为优先，不保留存在泄漏风险的虚高分数。
  ]
]

#slide(title: [多数据集统一架构])[
  #grid(
    columns: (1fr, 1fr),
    gutter: 18pt,
    [
      #insight-box(title: [已接入多个数据集])[
        - DGraph-Fin：官方图交易欺诈识别基准
        - DGraph-Fin2：带时间增强的图交易数据
        - IEEE-CIS：表格交易欺诈识别数据
        - Elliptic++：反洗钱交易网络数据
        - AMLSim：仿真交易与反洗钱样例
      ]
    ],
    [
      #table(
        columns: (1fr, 0.72fr, 1.25fr, 0.76fr),
        inset: 7pt,
        align: center + horizon,
        stroke: 0.45pt + forest-main.lighten(48%),
        fill: (x, y) => if y == 0 { forest-soft } else { paper },
        text(size: 12.5pt)[数据集], text(size: 12.5pt)[AUC], text(size: 12.5pt)[数据形态], text(size: 12.5pt)[表现],
        text(size: 12pt)[DGraph-Fin], text(size: 12pt)[0.828120], text(size: 12pt)[图交易网络], text(size: 12pt)[良好],
        text(size: 12pt)[DGraph-Fin2], text(size: 12pt)[0.827919], text(size: 12pt)[时间增强图], text(size: 12pt)[良好],
        text(size: 12pt)[IEEE-CIS], text(size: 12pt)[0.914582], text(size: 12pt)[表格交易], text(size: 12pt)[良好],
        text(size: 12pt)[Elliptic++], text(size: 12pt)[0.926556], text(size: 12pt)[反洗钱图], text(size: 12pt)[良好],
      )
      #v(0.7em)
      #accent-box(title: [统一架构的意义])[
        当前工程已经接入多个异构数据集，并在多个验证口径上取得稳定良好表现，体现了算法的可迁移性与泛化能力。
      ]
    ],
  )
]

= 实时大屏

#slide(title: [实时大屏核心界面一])[
  #grid(
    columns: (1fr, 1fr),
    gutter: 14pt,
    [
      #align(center)[#image("../../output/realtime/overview-redesign-live.png", width: 100%)]
      #set text(size: 12pt, fill: slate)
      实时交易监测与运行指标
    ],
    [
      #align(center)[#image("../../output/realtime/alerts-management.png", width: 100%)]
      #set text(size: 12pt, fill: slate)
      风险评分与告警队列
    ],
  )
]

#slide(title: [实时大屏核心界面二])[
  #grid(
    columns: (1fr, 1fr),
    gutter: 14pt,
    [
      #align(center)[#image("../../output/realtime/graph-management.png", width: 100%)]
      #set text(size: 12pt, fill: slate)
      团伙关系图与节点追溯
    ],
    [
      #align(center)[#image("../../output/realtime/review-management.png", width: 100%)]
      #set text(size: 12pt, fill: slate)
      复核结果与审计留痕
    ],
  )
]

#slide(title: [实时识别闭环])[
  #grid(
    columns: (1fr, 1fr),
    gutter: 18pt,
    [
      #insight-box(title: [核心能力])[
        - 仿真交易流实时刷新
        - 风险事件队列
        - 风险分、风险等级和欺诈判定
        - 渠道、金额、设备指纹与行为解释
        - 一跳邻域异常摘要
        - 处置动作、复核结论和审计输出
      ]
    ],
    [
      #accent-box(title: [识别闭环])[
        交易事件进入后，系统完成特征更新、模型评分、风险分层、风控动作生成和审计记录写入，形成从交易发生到处置留痕的在线闭环。
      ]
      #v(0.7em)
      #grid(
        columns: (1fr, 1fr),
        gutter: 10pt,
        [
          #stat-card([刷新方式], [2 秒轮询], note: [读取风险事件接口], fill: paper)
        ],
        [
          #stat-card([输出等级], [4 档], note: [low、medium、high、critical], fill: paper)
        ],
      )
    ],
  )
]

= 工程交付

#slide(title: [工程化与落地路线])[
  #grid(
    columns: (1fr, 1fr),
    gutter: 18pt,
    [
      #insight-box(title: [已经完成])[
        - `uv` 环境管理与锁文件
        - 统一 CLI 训练、汇总和面板构建
        - Typst 技术报告
        - 多数据集实验记录
        - 模型、指标、提交文件自动产出
        - 交易流回放与风险事件输出
        - 实时识别工作台
        - 风险等级、欺诈判定与审计输出
      ]
    ],
    [
      #accent-box(title: [已设计部署包])[
        - Kafka 接入交易流
        - Flink 维护时间窗口与增量特征
        - 在线推理服务返回风险分数
        - 结果消费者输出风控事件
        - Docker 部署包已静态验证
      ]
    ],
  )
  #v(0.7em)
  #block(
    width: 100%,
    inset: 12pt,
    radius: 14pt,
    fill: forest-soft,
    stroke: 0.6pt + forest-main.lighten(35%),
  )[
    #set text(fill: slate, size: 13pt)
    当前工程明确区分已实测的单机流式原型与仍需容器环境压测的 Kafka/Flink 部署包。
  ]
]

#slide(title: [系统能力与价值])[
  #grid(
    columns: (1fr, 1fr, 1fr),
    gutter: 14pt,
    [
      #stat-card([DGraph-Fin], [0.828120], note: [图识别链路已成型], fill: paper)
    ],
    [
      #stat-card([可信口径], [已完成复核], note: [Fin2、IEEE、Elliptic++ 均已校正口径], fill: paper)
    ],
    [
      #stat-card([工程展示], [已形成闭环], note: [报告、面板、记录、脚本], fill: paper)
    ],
  )
  #v(0.8em)
  #insight-box(title: [系统价值])[
    - 识别核心链路已经完成
    - 公开基准成绩可信，没有依赖明显泄漏
    - 实时识别工作台已经能演示仿真交易流识别、风险等级、处置和审计闭环
  ]
  #v(0.7em)
  #set align(center + horizon)
  #set text(fill: forest-main, weight: "semibold", size: 17pt)
  面向方向一的实时金融反诈识别系统
]

#slide(title: [附页])[
  #grid(
    columns: (1fr, 1fr),
    gutter: 20pt,
    [
      #insight-box(title: [系统边界])[
        - 聚焦方向一欺诈交易智能识别
        - 不展示参赛身份信息
        - 核心内容聚焦数据、模型、系统和结果
      ]
    ],
    [
      #accent-box(title: [技术重点])[
        - DGraph-Fin 识别链路
        - 可信验证与反泄漏
        - 可视化证据和工程闭环
      ]
    ],
  )
]
