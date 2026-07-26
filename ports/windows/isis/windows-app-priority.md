# ISIS 10 Windows APP 移植优先级

- 固定源码提交：`524eec10a7b0ffa2c591fb7f8bc82b3223bc6904`
- APP 总数：365
- 便利性和重要性均采用 1–5 分；综合分为 `重要性×10+便利性`，因此任务价值优先、同等级再优先选择易移植项。
- 该表是源码级规划清单，不等同于 Windows 编译或科学结果验证。

## 建议批次统计

| 批次 | 数量 |
|---|---:|
| W0-current-batch | 149 |
| W3-general-easy | 17 |
| W4-medium | 185 |
| W5-GUI | 6 |
| W5-blocked-or-specialized | 8 |

## 综合优先级前 40

| 排名 | APP | 模块 | 便利性 | 重要性 | 建议批次 | 阻塞因素 |
|---:|---|---|---:|---:|---|---|
| 1 | automos | base | 5 | 5 | W0-current-batch | none |
| 2 | caminfo | base | 5 | 5 | W0-current-batch | none |
| 3 | campt | base | 5 | 5 | W0-current-batch | none |
| 4 | camrange | base | 5 | 5 | W0-current-batch | none |
| 5 | footprintinit | base | 5 | 5 | W0-current-batch | none |
| 6 | footprintmerge | base | 5 | 5 | W0-current-batch | none |
| 7 | map2map | base | 5 | 5 | W0-current-batch | none |
| 8 | mapmos | base | 5 | 5 | W0-current-batch | none |
| 9 | mappt | base | 5 | 5 | W0-current-batch | none |
| 10 | maptemplate | base | 5 | 5 | W0-current-batch | none |
| 11 | mosrange | base | 5 | 5 | W0-current-batch | none |
| 12 | spicefit | base | 5 | 5 | W0-current-batch | none |
| 13 | jigsaw | control | 5 | 5 | W0-current-batch | none |
| 14 | cam2map | base | 3 | 5 | W0-current-batch | external_process |
| 15 | spiceinit | base | 3 | 5 | W0-current-batch | posix_api |
| 16 | pointreg | control | 3 | 5 | W0-current-batch | posix_api |
| 17 | findfeatures | control | 1 | 5 | W5-blocked-or-specialized | external_process;large_source;optional_stack |
| 18 | ascii2isis | base | 5 | 4 | W0-current-batch | none |
| 19 | camstats | base | 5 | 4 | W0-current-batch | none |
| 20 | catlab | base | 5 | 4 | W0-current-batch | none |
| 21 | crop | base | 5 | 4 | W0-current-batch | none |
| 22 | cubeatt | base | 5 | 4 | W0-current-batch | none |
| 23 | cubediff | base | 5 | 4 | W0-current-batch | none |
| 24 | cubeit | base | 5 | 4 | W0-current-batch | none |
| 25 | dsk2isis | base | 5 | 4 | W0-current-batch | none |
| 26 | findimageoverlaps | base | 5 | 4 | W0-current-batch | none |
| 27 | fits2isis | base | 5 | 4 | W0-current-batch | none |
| 28 | fx | base | 5 | 4 | W0-current-batch | none |
| 29 | getkey | base | 5 | 4 | W0-current-batch | none |
| 30 | isis2fits | base | 5 | 4 | W0-current-batch | none |
| 31 | isis2pds | base | 5 | 4 | W0-current-batch | none |
| 32 | isis2std | base | 5 | 4 | W0-current-batch | none |
| 33 | makecube | base | 5 | 4 | W0-current-batch | none |
| 34 | map2cam | base | 5 | 4 | W0-current-batch | none |
| 35 | mapgrid | base | 5 | 4 | W0-current-batch | none |
| 36 | maplab | base | 5 | 4 | W0-current-batch | none |
| 37 | maptrim | base | 5 | 4 | W0-current-batch | none |
| 38 | pds2isis | base | 5 | 4 | W0-current-batch | none |
| 39 | raw2isis | base | 5 | 4 | W0-current-batch | none |
| 40 | reduce | base | 5 | 4 | W0-current-batch | none |

## 使用说明

- `W1`：高价值且预计容易移植，优先进入下一批。
- `W2`：高价值但存在中等平台风险，应单独编译定位。
- `W3`：通用、易移植，可用于扩大覆盖面。
- `W4`：中等优先级，等待核心链路稳定后推进。
- `W5-GUI`：Qt GUI 单独成线，不与 CLI 批次混编。
- `W5-blocked-or-specialized`：存在直接平台阻塞或任务用途较窄。

完整 365 项及源码证据见 `windows-app-priority.csv`。
