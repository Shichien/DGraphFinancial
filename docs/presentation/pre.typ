#import "@preview/touying:0.6.1": *
#import "template/theme.typ": *
#import "template/components.typ": *

#show: deck-theme((
  title: [金融反诈智能守护],
  subtitle: [方向一 欺诈交易智能识别],
  author: [参赛团队],
  date: [2026-06-03],
  institution: [方向一 欺诈交易智能识别答辩],
))

#set page(fill: paper)
#set text(font: ("Microsoft YaHei", "SimSun"), fill: slate)

#title-slide()

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
        - 项目：DGCheater 金融反诈智能守护
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
    本版本为正式提交展示材料，不包含参赛身份信息。
  ]
]

#slide(title: [项目定位])[
  #grid(
    columns: (1.05fr, 0.95fr),
    gutter: 20pt,
    [
      #insight-box(title: [作品边界])[
        我们聚焦赛道一的交易反欺诈识别，而不是泛化做一个大而全的反诈平台。

        当前作品重点完成三件事：

        - 可复现的主识别链路
        - 可信的离线评测口径
        - 能直接答辩展示的工程闭环
      ]
      #v(0.7em)
      #accent-box(title: [为什么值得讲])[
        欺诈交易不是单点异常，而是时间行为、关系结构与风险传播共同作用。赛道一更看重能否把这三类信息组织成闭环。
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
          #stat-card([已跑通数据集], [5+], note: [DGraph-Fin、Fin2、IEEE-CIS、Elliptic++、AMLSim], fill: rgb("#eef7f0"))
        ],
        [
          #grid.cell(colspan: 2)[
            #stat-card([交付形态], [模型 + 报告 + 面板], note: [CLI、Typst、Dashboard], fill: rgb("#fffaf0"), accent: amber.darken(25%))
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
      #insight-box(title: [必须讲清楚])[
        - 数据如何表示交易关系与时间
        - 特征如何覆盖结构、时间和风险传播
        - 模型如何输出风险分数
        - 为什么结果可信
      ]
    ],
    [
      #accent-box(title: [不必过度承诺])[
        - 不把赛道二、赛道三混入主叙事
        - 不把 GNN 说成唯一方案
        - 不把在线系统说成已经完整落地
        - 不把公开数据高分当成当前可复现结果
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
    #set text(fill: forest-deep, weight: "bold", size: 14pt)
    核心表达不是做了很多模块，而是围绕欺诈交易识别做成了一条可信主链路。
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

#slide(title: [可信结果链])[
  #grid(
    columns: (1fr, 1fr, 1fr),
    gutter: 12pt,
    [
      #stat-card([DGraph-Fin], [0.828120], note: [公开图基准], fill: rgb("#f5f8f6"))
    ],
    [
      #stat-card([DGraph-Fin2], [0.827919], note: [移除节点时间标签], fill: rgb("#eef7f0"))
    ],
    [
      #stat-card([IEEE-CIS], [0.914582], note: [时间切分验证], fill: rgb("#fff8e8"), accent: amber.darken(25%))
    ],
    [
      #grid.cell(colspan: 2)[
        #insight-box(title: [这条链路说明什么])[
          - 保留公开图基准、时间增强图和表格交易验证
          - 不直接使用存在泄漏风险的字段
          - 统一流程输出指标、提交文件和特征重要度
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
    可信性不是附加说明，而是作品能力。我们更愿意交一个解释得住的成绩，而不是保留一个更高但经不起追问的数字。
  ]
]

#slide(title: [多数据集统一架构])[
  #grid(
    columns: (1fr, 1fr),
    gutter: 18pt,
    [
      #insight-box(title: [已接入数据形态])[
        - 官方 DGraph-Fin
        - 时间增强版 DGraph-Fin2
        - 表格交易欺诈 IEEE-CIS
        - AML actor 图 Elliptic++
        - AMLSim 仿真样例
      ]
    ],
    [
      #grid(
        columns: (1fr, 1fr),
        gutter: 10pt,
        [
          #stat-card([DGraph-Fin], [0.828120], note: [官方基础图数据], fill: paper)
        ],
        [
          #stat-card([DGraph-Fin2], [0.827919], note: [去泄漏后稳定结果], fill: paper)
        ],
        [
          #stat-card([IEEE-CIS], [0.914582], note: [时间切分可信结果], fill: paper)
        ],
        [
          #stat-card([Elliptic++], [0.926556], note: [修正规则后严格复核], fill: paper)
        ],
      )
      #v(0.7em)
      #accent-box(title: [统一架构的意义])[
        当前工程不是只对一个文件写死的脚本，而是一套可迁移的反诈识别框架。
      ]
    ],
  )
]

#slide(title: [可解释展示闭环])[
  #grid(
    columns: (0.86fr, 1.14fr),
    gutter: 18pt,
    [
      #insight-box(title: [答辩展示已经补齐])[
        - 可信成绩与公开方案对照
        - 匿名关系子图与推理主链路
        - 四类仿真欺诈剧本
        - 一键生成仿真场景
        - 模型识别结果与阈值命中量
        - 调查控制台、处理状态与复核结论
        - 风险解释、建议动作与审计记录
      ]
      #v(0.7em)
      #accent-box(title: [价值])[
        这样答辩现场不会只剩分数表和 PDF，而是能从仿真场景讲到模型识别、案件处置、人工复核和一跳溯源证据。
      ]
    ],
    [
      #image("assets/dashboard.png", width: 100%)
      #v(0.35em)
      #grid(
        columns: (1fr, 1fr),
        gutter: 8pt,
        [#chip([可信成绩])],
        [#chip([公开对照])],
        [#chip([场景生成])],
        [#chip([模型识别])],
        [#chip([阈值命中])],
        [#chip([调查控制台])],
        [#chip([复核结论])],
        [#chip([审计记录])],
      )
      #v(0.35em)
      #set text(fill: slate, size: 11pt)
      输出文件：`output/dashboard/index.html`
    ],
  )
]

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
        - 阈值命中量与模型版本展示
        - 调查控制台与审计记录展示
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
    当前更稳妥的答辩策略，是明确区分已实测的单机流式原型与仍需容器环境压测的 Kafka/Flink 部署包。
  ]
]

#slide(title: [当前交付与价值])[
  #grid(
    columns: (1fr, 1fr, 1fr),
    gutter: 14pt,
    [
      #stat-card([DGraph-Fin], [0.828120], note: [图识别链路已成型], fill: paper)
    ],
    [
      #stat-card([可信口径], [已主动排雷], note: [Fin2、IEEE、Elliptic++ 都做了复核], fill: paper)
    ],
    [
      #stat-card([工程展示], [已形成闭环], note: [报告、面板、记录、脚本], fill: paper)
    ],
  )
  #v(0.8em)
  #insight-box(title: [答辩结论])[
    - 识别核心链路已经完成
    - 公开基准成绩可信，没有依赖明显泄漏
    - 大屏已经能现场演示仿真、识别、处置和审计闭环
  ]
  #v(0.7em)
  #set align(center + horizon)
  #set text(fill: forest-main, weight: "bold", size: 17pt)
  谢谢各位老师
]

#slide(title: [附页信息])[
  #grid(
    columns: (1fr, 1fr),
    gutter: 20pt,
    [
      #insight-box(title: [提交材料边界])[
        - 保留作品名称、任务方向和技术路线
        - 不展示参赛身份信息
        - 演示内容聚焦数据、模型、系统和结果
      ]
    ],
    [
      #accent-box(title: [现场答辩重点])[
        - DGraph-Fin 识别链路
        - 可信验证与反泄漏
        - 可视化证据和工程闭环
      ]
    ],
  )
]
