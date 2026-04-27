# 论文图注草稿（中英双语）

用途：为以下三张图提供可直接粘贴到论文、补充材料或图注管理文档中的中英文图注草稿。

对应图稿：
- `reference/notes/lowres-offset-flowchart-mermaid-zh.md`
- `reference/notes/image-match-end-to-end-flowchart-mermaid-zh.md`
- `reference/notes/image-match-dataflow-diagram-mermaid-zh.md`

建议排版方案：
- **方案 A（三联版）**：将三张图拼为一个总图，作为 Figure 1，其中包含子图 **(a)**、**(b)**、**(c)**。
- **方案 B（分图版）**：将子图 **(a)** 与 **(b)** 作为 Figure 1，将子图 **(c)** 单独作为 Figure 2。

---

## 方案 A：Figure 1 三联版总图注

### 中文总图注

**图 1.** 基于 DOM 的匹配管线示意图，包括：（a）低分辨率粗偏移估计与可靠性门控流程；（b）从低分辨率粗偏移到 RANSAC 几何过滤的整体匹配链路；（c）关键数据结构在匹配管线中的创建、传递与写出关系。子图（a）说明了低分辨率粗偏移仅在通过匹配数、单应矩阵可用性与重投影误差等可靠性约束后才会被接受，否则回退为零偏移。子图（b）展示了粗偏移如何参与投影重叠区准备、tile 级匹配以及最终的 RANSAC 几何过滤。子图（c）进一步给出了 `PairPreparationMetadata`、`PairedTileWindow`、`KeypointFile` 与 `ransac_summary` 等关键对象在不同模块之间的流转关系。

### English overall caption

**Fig. 1.** Schematic overview of the DOM-based matching pipeline, including (a) coarse low-resolution offset estimation with reliability gating, (b) the end-to-end matching chain from coarse low-resolution offset estimation to RANSAC-based geometric filtering, and (c) the creation, propagation, and output of key data structures in the pipeline. Panel (a) shows that the coarse offset estimate is accepted only after passing reliability checks such as retained match count, homography availability, and reprojection error; otherwise, the pipeline falls back to zero offset. Panel (b) illustrates how the coarse offset is used in projected-overlap preparation, tile-level matching, and final RANSAC-based geometric filtering. Panel (c) further summarizes the flow of key objects, including `PairPreparationMetadata`, `PairedTileWindow`, `KeypointFile`, and `ransac_summary`, across modules.

---

## 方案 A：子图分注（适合 subcaption）

### 子图（a）

#### 中文

**（a）低分辨率粗偏移估计与可靠性门控流程。** 该子图展示了 `estimate_low_resolution_projected_offset(...)` 的完整执行路径。低分辨率粗偏移仅在通过保留匹配数、RANSAC 单应矩阵可用性、平均重投影误差以及最大平均投影偏移等门控条件后才会被接受；否则，流程将统一回退为零偏移。

#### English

**(a) Coarse low-resolution offset estimation with reliability gating.** This panel shows the full execution path of `estimate_low_resolution_projected_offset(...)`. The coarse offset is accepted only after passing gating conditions on retained match count, RANSAC homography availability, mean reprojection error, and the maximum mean projected offset; otherwise, the procedure consistently falls back to zero offset.

### 子图（b）

#### 中文

**（b）从低分辨率粗偏移到 RANSAC 几何过滤的整体匹配链路。** 该子图概括了 `match_dom_pair(...)` 的主要处理阶段，包括低分辨率粗偏移估计、投影重叠区准备、tile 级匹配以及最终的 RANSAC 几何过滤，并显式保留了关键跳过分支与成功输出分支。

#### English

**(b) End-to-end matching pipeline from coarse low-resolution offset estimation to RANSAC filtering.** This panel summarizes the main stages of `match_dom_pair(...)`, including coarse low-resolution offset estimation, projected-overlap preparation, tile-level matching, and final RANSAC-based geometric filtering, while explicitly retaining both the main skip branches and the successful output branch.

### 子图（c）

#### 中文

**（c）关键数据结构在匹配管线中的创建、传递与写出关系。** 该子图从对象流视角总结了 `PairPreparationMetadata`、`PairedTileWindow`、`KeypointFile` 与 `ransac_summary` 等关键结构在不同模块之间的输入输出关系，可用于辅助解释模块契约与中间结果组织方式。

#### English

**(c) Creation, propagation, and output of key data structures in the matching pipeline.** This panel summarizes, from a dataflow perspective, how key structures such as `PairPreparationMetadata`, `PairedTileWindow`, `KeypointFile`, and `ransac_summary` are produced, consumed, and written across modules, thereby clarifying module contracts and intermediate result organization.

---

## 方案 B：Figure 1 / Figure 2 分拆图注

### Figure 1（建议包含子图 a、b）

#### 中文

**图 1.** DOM 匹配方法流程总览，包括：（a）低分辨率粗偏移估计与可靠性门控流程；（b）从低分辨率粗偏移到 RANSAC 几何过滤的整体匹配链路。该图强调从粗配准到几何过滤的核心算法路径，并保留关键回退和跳过分支，以说明方法在复杂输入条件下的稳健性设计。

#### English

**Fig. 1.** Overview of the DOM matching method, including (a) coarse low-resolution offset estimation with reliability gating and (b) the end-to-end matching chain from coarse low-resolution offset estimation to RANSAC-based geometric filtering. This figure emphasizes the core algorithmic path from coarse alignment to geometric filtering, while retaining major fallback and skip branches to highlight the robustness-oriented design of the pipeline under challenging inputs.

### Figure 2（建议包含子图 c）

#### 中文

**图 2.** 匹配管线中的关键数据结构流转关系。图中总结了 `PairPreparationMetadata`、`PairedTileWindow`、原始与过滤后 `KeypointFile` 以及 `ransac_summary` 等对象在不同模块之间的创建、传递与写出方式，用于补充说明实现层面的模块组织与结果汇总逻辑。

#### English

**Fig. 2.** Dataflow of key structures in the matching pipeline. The figure summarizes how objects such as `PairPreparationMetadata`, `PairedTileWindow`, raw and filtered `KeypointFile` instances, and `ransac_summary` are created, propagated, and written across modules, thereby complementing the implementation-level organization of the pipeline and its result aggregation logic.

---

## 用词统一建议（写论文正文时可直接沿用）

### 中文术语

- 低分辨率粗偏移：low-resolution coarse offset
- 投影重叠区准备：projected-overlap preparation
- 原始匹配点集：raw matched keypoint set
- 过滤后匹配点集：RANSAC-filtered keypoint set
- RANSAC 汇总：RANSAC summary
- 回退为零偏移：fallback to zero offset

### English terms

- low-resolution coarse offset
- projected-overlap preparation
- raw matched keypoint set
- RANSAC-filtered keypoint set
- RANSAC summary
- fallback to zero offset