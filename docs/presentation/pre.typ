#import "@preview/touying:0.6.1": *
#import "template/theme.typ": *
#import "template/components.typ": *

#show: deck-theme((
  title: [金融反诈智能守护],
  subtitle: [方向一 欺诈交易智能识别],
  author: [参赛团队],
  date: [2026-06-03],
  institution: [方向一 欺诈交易智能识别],
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
          #stat-card([已接入数据集], [5+], note: [DGraph-Fin、Fin2、IEEE-CIS、Elliptic++、AMLSim], fill: rgb("#eef7f0"))
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
        - 图神经网络作为后续增强方向
        - 在线系统当前为原型闭环
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
    #set text(fill: forest-deep, weight: "bold", size: 14pt)
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
        #insight-box(title: [结果含义])[
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
    可信性是本方案的重要能力。结果以可解释、可复核为优先，不保留存在泄漏风险的虚高分数。
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
        当前工程不是面向单一文件的临时脚本，而是一套可迁移的反诈识别框架。
      ]
    ],
  )
]

#slide(title: [展示内容迁移])[
  #grid(
    columns: (0.86fr, 1.14fr),
    gutter: 18pt,
    [
      #insight-box(title: [放入文档和演示稿])[
        - 可信成绩与公开方案对照
        - 匿名关系子图与推理主链路
        - 四类仿真欺诈剧本
        - 数据资产、字段结构和验证口径
        - 工程交付证据与下一步计划
        - 安全合规与可解释性说明
      ]
      #v(0.7em)
      #accent-box(title: [前端边界])[
        前端定位为实时识别工作台，只保留仿真交易流发生时的实时识别、动态异常检测、风险评估、欺诈判定和风险等级输出。
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
        [#chip([关系子图])],
        [#chip([推理链路])],
        [#chip([仿真剧本])],
        [#chip([数据资产])],
        [#chip([交付证据])],
        [#chip([评估口径])],
      )
      #v(0.35em)
      #set text(fill: slate, size: 11pt)
      展示性叙事由本演示稿和报告承载
    ],
  )
]

#slide(title: [实时识别工作台])[
  #grid(
    columns: (1fr, 1fr),
    gutter: 18pt,
    [
      #insight-box(title: [页面只保留])[
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
        交易事件进入后，系统完成特征更新、模型评分、风险分层、风控动作生成和审计记录写入。页面只呈现这个在线闭环，不再重复报告内容。
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

#slide(title: [当前交付与价值])[
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
  #insight-box(title: [作品总结])[
    - 识别核心链路已经完成
    - 公开基准成绩可信，没有依赖明显泄漏
    - 实时识别工作台已经能演示仿真交易流识别、风险等级、处置和审计闭环
  ]
  #v(0.7em)
  #set align(center + horizon)
  #set text(fill: forest-main, weight: "bold", size: 17pt)
  金融反诈智能守护方向一作品材料
]

#slide(title: [附页])[
  #grid(
    columns: (1fr, 1fr),
    gutter: 20pt,
    [
      #insight-box(title: [材料边界])[
        - 保留作品名称、任务方向和技术路线
        - 不展示参赛身份信息
        - 演示内容聚焦数据、模型、系统和结果
      ]
    ],
    [
      #accent-box(title: [材料重点])[
        - DGraph-Fin 识别链路
        - 可信验证与反泄漏
        - 可视化证据和工程闭环
      ]
    ],
  )
]
