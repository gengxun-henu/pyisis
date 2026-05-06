flowchart TD
    A[输入单个立体像对<br/>left_dom.cub + right_dom.cub] --> B[读取配置与参数<br/>band / tile size / SIFT / 阈值 / 并行设置]
    B --> C{是否启用低分辨率粗配准?}

    C -- 是 --> D[生成或复用低分辨率 DOM<br/>ISIS reduce / precomputed low-res DOM]
    D --> E[低分辨率 SIFT 匹配]
    E --> F[低分辨率 RANSAC 过滤]
    F --> G{粗配准结果是否可信?\n匹配点数 / 重投影误差 / 平均投影偏移}
    G -- 是 --> H[估计全局 projected offset<br/>delta_x / delta_y]
    G -- 否 --> I[回退为零偏移]

    C -- 否 --> I
    H --> J[准备 full-resolution overlap crop]
    I --> J

    J --> K{overlap window 是否有效?}
    K -- 否 --> Z1[结束<br/>status = skipped / no overlap]
    K -- 是 --> L[生成 shared extent 与 paired tile windows]

    L --> M{是否启用 tile-validity prefilter?}
    M -- 是 --> N[基于 DOM validity index<br/>预过滤明显无效 tile]
    M -- 否 --> O[直接进入全部候选 tile]
    N --> O

    O --> P{tile 数量 > 1 且启用 CPU 并行?}
    P -- 是 --> Q[多进程批量 tile matching<br/>worker 复用 opened cubes]
    P -- 否 --> R[串行 tile matching]

    Q --> S[逐 tile 处理]
    R --> S

    S --> S1[读取 tile / 灰度拉伸 / invalid mask 扩张]
    S1 --> S2[检测 SIFT 特征]
    S2 --> S3[描述子匹配<br/>BF 或 FLANN + ratio test]
    S3 --> S4[保留有效 tile 匹配点]
    S4 --> T[汇总所有 tile 的匹配点]

    T --> U[写出 DOM-space .key 文件<br/>left.key + right.key]
    U --> V[写 metadata JSON<br/>tile 统计 / low-res offset / 并行信息]
    V --> W{是否写匹配可视化?}
    W -- 是 --> X[输出 pre-RANSAC drawMatches PNG]
    W -- 否 --> Y[返回匹配结果摘要]
    X --> Y

    Y --> Z[输出给下一阶段<br/>controlnet_stereopair.py from-dom-batch]