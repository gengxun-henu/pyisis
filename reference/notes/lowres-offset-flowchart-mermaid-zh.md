# 子图（a）低分辨率粗偏移估计流程图（Mermaid，中文）

建议论文子图编号：**(a)**

建议中文子图标题：**低分辨率粗偏移估计与可靠性门控流程**

Suggested English panel title: **Coarse Low-Resolution Offset Estimation with Reliability Gating**

用途：展示 `examples/controlnet_construct/lowres_offset.py` 中
`estimate_low_resolution_projected_offset(...)` 的完整主流程、可靠性判定分支与成功出口。

本三联版统一术语如下：
- “低分辨率粗偏移”统一对应 `low_resolution_offset_summary` 中的粗投影平移估计；
- “投影重叠区准备”统一对应 `prepare_dom_pair_for_matching(...)`；
- “原始匹配点集 / 过滤后匹配点集”统一对应 `KeypointFile` 在 RANSAC 前后的状态；
- “回退为零偏移”统一表示 `fallback_zero` 路径。

说明：
- 该版本面向论文子图三联排版，标题、节点句式与其他两图已统一。
- 节点配色采用低饱和蓝/金/红/绿体系，适合后续导出 SVG 后再做 IEEE TGRS 风格排版。
- 可直接复制下方 Mermaid 源码块到支持 Mermaid 的 Markdown 渲染器中使用。

```mermaid
flowchart TD
    classDef start fill:#16324f,stroke:#0b1f33,color:#ffffff,stroke-width:1.6px;
    classDef process fill:#eef4fb,stroke:#4c78a8,color:#10243e,stroke-width:1.1px;
    classDef decision fill:#fff7e6,stroke:#d9a441,color:#5a3b00,stroke-width:1.1px;
    classDef fallback fill:#fff1f0,stroke:#c44536,color:#6b1f17,stroke-width:1.1px;
    classDef success fill:#edf8ee,stroke:#4f9d69,color:#123524,stroke-width:1.1px;
    classDef io fill:#f4f1fb,stroke:#7a5ea6,color:#2c1e47,stroke-width:1.1px;

    A([开始：estimate_low_resolution_projected_offset]):::start --> B[校验参数：\ntrim 比例、重投影误差阈值、\n最小保留匹配数、最大投影偏移阈值]:::process
    B --> C{是否启用低分辨率粗偏移估计？}:::decision
    C -- 否 --> C0[返回 disabled：\nΔx=0，Δy=0\n说明：功能关闭，并非失败回退]:::io
    C -- 是 --> D[初始化：\n解析 level、创建输出目录、开始计时]:::process
    D --> E[检查外部命令 reduce 是否可用]:::process
    E --> F[生成左右低分辨率 DOM：\nlevel=0 直接复制；\nlevel>0 调用 reduce 缩小]:::process
    F --> G[在低分辨率 DOM 上调用 match_dom_pair：\n执行整图粗匹配，不再递归 lowres]:::process
    G --> H[写出原始匹配点集：\nraw_A.key / raw_B.key]:::io
    H --> I[执行 RANSAC 过滤：\nfilter_stereo_pair_keypoints_with_ransac]:::process
    I --> J[写出过滤后匹配点集：\nA.key / B.key]:::io
    J --> K{保留匹配数 > 0？}:::decision
    K -- 否 --> K0[回退为零偏移：\nno_matches]:::fallback
    K -- 是 --> L{保留匹配数\n达到最小阈值？}:::decision
    L -- 否 --> L0[回退为零偏移：\nretained_match_count_below_threshold]:::fallback
    L -- 是 --> M{RANSAC 是否成功应用？}:::decision
    M -- 否 --> M0[回退为零偏移：\nhomography_failed 或\ninsufficient_points_for_homography]:::fallback
    M -- 是 --> N{homography_matrix 是否存在？}:::decision
    N -- 否 --> N0[回退为零偏移：\nhomography_failed]:::fallback
    N -- 是 --> O[计算每对点的重投影误差：\n使用 homography 将左点投影到右图]:::process
    O --> P[对重投影误差做 trimmed mean\n抑制少量离群点影响]:::process
    P --> Q{平均重投影误差\n是否不超过阈值？}:::decision
    Q -- 否 --> Q0[回退为零偏移：\nreprojection_error_above_threshold]:::fallback
    Q -- 是 --> R[打开左右低分辨率 Cube]:::process
    R --> S[批量将保留匹配点从\nsample/line 转成 projected XY]:::process
    S --> T[逐点计算粗投影偏移：\nΔx = x_right - x_left\nΔy = y_right - y_left]:::process
    T --> U[分别对 Δx 与 Δy 做 trimmed mean]:::process
    U --> V[计算平均投影偏移模长：\nmean_projected_offset_meters]:::process
    V --> W{若启用最大偏移阈值，\n是否超限？}:::decision
    W -- 是 --> W0[回退为零偏移：\nmean_projected_offset_above_threshold]:::fallback
    W -- 否 --> X[输出低分辨率匹配可视化：\nlow_resolution_ransac.png]:::io
    X --> Y([返回 succeeded：\n输出 delta_x_projected / delta_y_projected\n并附带 raw summary、ransac summary 与诊断信息]):::success

    E -.运行时异常.-> Z[捕获异常]:::fallback
    F -.运行时异常.-> Z
    G -.运行时异常.-> Z
    I -.运行时异常.-> Z
    O -.运行时异常.-> Z
    R -.运行时异常.-> Z
    X -.运行时异常.-> Z
    Z --> Z0[统一回退：fallback_zero\nreason=other_runtime_failure\nΔx=0，Δy=0]:::fallback
```

论文拼图建议：
- 作为三联图的 **(a)** 放置在左侧；
- 推荐与子图（b）共享相近宽度，与子图（c）保持相同字体；
- 导出后可在矢量编辑器中添加子图角标 “(a)”。
