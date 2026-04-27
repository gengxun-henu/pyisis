# 子图（c）关键数据结构流转图（Mermaid，中文）

建议论文子图编号：**(c)**

建议中文子图标题：**关键数据结构在匹配管线中的创建、传递与写出关系**

Suggested English panel title: **Creation, Propagation, and Output of Key Data Structures in the Matching Pipeline**

用途：专门展示 `PairPreparationMetadata`、`PairedTileWindow`、`KeypointFile`、`ransac_summary` 等关键对象，
在 `lowres_offset.py`、`dom_prepare.py`、`tile_matching.py`、`stereo_ransac.py` 与 `image_match.py` 之间如何创建、传递与写出。

本三联版统一术语如下：
- “原始匹配点集”统一指 RANSAC 前的 `KeypointFile`；
- “过滤后匹配点集”统一指 RANSAC 后输出的 `KeypointFile`；
- “投影重叠区准备结果”统一指 `PairPreparationMetadata`；
- “RANSAC 汇总”统一指 `ransac_summary`。

说明：
- 本图采用“对象流 / 数据血缘”视角，不强调算法先后，而强调模块之间的输入输出契约。
- 建议作为三联图中的解释性子图，与子图（a）（b）配合使用。
- 图中保留 `metadata_output`、`.key` 文件与最终汇总出口，便于联动调试与论文方法说明。

```mermaid
flowchart LR
    classDef module fill:#16324f,stroke:#0b1f33,color:#ffffff,stroke-width:1.5px;
    classDef object fill:#eef4fb,stroke:#4c78a8,color:#10243e,stroke-width:1.1px;
    classDef detail fill:#f7fbff,stroke:#6b8fb8,color:#16324f,stroke-width:1px;
    classDef gate fill:#fff7e6,stroke:#d9a441,color:#5a3b00,stroke-width:1.1px;
    classDef result fill:#edf8ee,stroke:#4f9d69,color:#123524,stroke-width:1.1px;
    classDef side fill:#f4f1fb,stroke:#7a5ea6,color:#2c1e47,stroke-width:1px;

    IM["image_match.py<br/>match_dom_pair"]:::module --> LO["lowres_offset.py<br/>estimate_low_resolution_projected_offset"]:::module
    LO --> LOS["low_resolution_offset_summary<br/>低分辨率粗偏移汇总<br/>- delta_x_projected<br/>- delta_y_projected<br/>- retained_match_count<br/>- trimmed_mean_reprojection_error_pixels<br/>- image_match_summary<br/>- ransac_summary"]:::object
    LOS --> IM

    IM --> DP["dom_prepare.py<br/>prepare_dom_pair_for_matching"]:::module
    DP --> PPM["PairPreparationMetadata<br/>投影重叠区准备结果<br/>- left: CropWindow<br/>- right: CropWindow<br/>- overlap / expanded bounds<br/>- shared_width / shared_height<br/>- status / reason<br/>- projected_delta_x / projected_delta_y"]:::object
    PPM --> IM
    PPM --> META["write_pair_preparation_metadata<br/>JSON sidecar / metadata_output"]:::side

    IM --> TW["_paired_windows<br/>tile_matching.py"]:::module
    PPM --> TW
    TW --> PTW["PairedTileWindow 列表<br/>每项包含：<br/>- local_window<br/>- left_window<br/>- right_window"]:::object
    PTW --> EXEC{"串行还是并行执行？"}:::gate

    EXEC -->|串行| SER[_run_serial_tile_match_tasks]:::module
    EXEC -->|并行| PAR["_build_tile_match_tasks +<br/>_run_parallel_tile_match_tasks"]:::module
    PAR --> TMT["TileMatchTask 列表<br/>把路径、窗口、SIFT 参数、<br/>阈值配置打包给 worker"]:::object
    TMT --> PAR

    SER --> TM["_match_tile_from_window_values"]:::module
    PAR --> TM
    PTW --> TM
    TM --> TMR["TileMatchResult<br/>- stats: TileMatchStats<br/>- left_points: tuple[Keypoint]<br/>- right_points: tuple[Keypoint]"]:::object
    TMR --> IM

    IM --> KFL["原始匹配点集 KeypointFile 左侧<br/>image_width / image_height / points"]:::object
    IM --> KFR["原始匹配点集 KeypointFile 右侧<br/>image_width / image_height / points"]:::object
    IM --> IMS["image_match summary<br/>- low_resolution_offset<br/>- preparation<br/>- tiles<br/>- matcher diagnostics<br/>- point_count"]:::object
    KFL --> RAW["write_key_file<br/>raw_A.key"]:::side
    KFR --> RAWB["write_key_file<br/>raw_B.key"]:::side
    IMS --> META2["metadata_payload.image_match"]:::side

    KFL --> SR["stereo_ransac.py<br/>filter_stereo_pair_keypoints_with_ransac"]:::module
    KFR --> SR
    SR --> RSUM["ransac_summary<br/>RANSAC 汇总<br/>- applied / status / mode<br/>- input_count / retained_count / dropped_count<br/>- opencv_inlier_count / opencv_outlier_count<br/>- retained_soft_outlier_count<br/>- homography_matrix"]:::object
    SR --> FKFL["过滤后匹配点集 KeypointFile 左侧"]:::result
    SR --> FKFR["过滤后匹配点集 KeypointFile 右侧"]:::result

    FKFL --> OUTA["write_key_file<br/>filtered_A.key 或最终输出 key"]:::side
    FKFR --> OUTB["write_key_file<br/>filtered_B.key 或最终输出 key"]:::side
    RSUM --> FINAL["最终返回 / 元数据汇总<br/>供下游 controlnet 构建或诊断使用"]:::result
    IMS --> FINAL
    PPM --> FINAL
    LOS --> FINAL
```

论文拼图建议：
- 作为三联图的 **(c)** 放置在右侧，承担“解释性补图”角色；
- 若主文版面有限，可放入补充材料或作为 Figure 2 的一部分；
- 导出后推荐在左上角补充角标 “(c)”。
