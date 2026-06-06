# Representative 4-Pair Test Summary

Output root:
`/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_tile_routing_representative_4pair_20260604`

## Case Set

| Case | Latitude bin | Texture/lighting class | Pair tag |
| --- | --- | --- | --- |
| near_pole_sparse | south-85-to-89.9 | sparse-inconsistent | `REDUCED_M1109027420LE.echo.cal__REDUCED_M140550700LE.echo.cal` |
| near_pole_rich | south-85-to-89.9 | rich-inconsistent | `REDUCED_M1203964116RE.echo.cal__REDUCED_M140577849LE.echo.cal` |
| near_80S_sparse | south-80-to-82 | sparse-inconsistent | `REDUCED_M1232286275LE.echo.cal__REDUCED_M173554018RE.echo.cal` |
| near_80S_rich | south-80-to-82 | rich-consistent | `REDUCED_M1137240043RE.echo.cal__REDUCED_M1137247155LE.echo.cal` |

## Method Totals

| Method | Raw matches | RANSAC retained | Successful pairs (retained >= 4) |
| --- | ---: | ---: | ---: |
| SIFT+FLANN | 131 | 25 | 4 |
| SIFT+LightGlue | 344 | 35 | 3 |
| SuperPoint+LightGlue | 339 | 45 | 4 |
| LoFTR | 3429 | 61 | 4 |
| Adaptive-tile | 249 | 37 | 4 |

## Adaptive-Tile Route Evidence

| Case | Valid tiles | Classic tasks | Classic matches | Deep route candidates | Exported deep tasks | Skipped deep tasks | Adaptive retained |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| near_pole_sparse | 12 | 6 | 25 | 6 | 0 | 6 | 11 |
| near_pole_rich | 5 | 0 | 0 | 5 | 1 | 4 | 8 |
| near_80S_sparse | 3 | 2 | 22 | 1 | 0 | 1 | 5 |
| near_80S_rich | 9 | 9 | 176 | 0 | 0 | 0 | 13 |

## Interpretation

This four-case rerun is deliberately representative rather than exhaustive: two near-pole pairs and two near-80S pairs, with one sparse and one rich texture case in each latitude regime.

The main claim supported by this subset is not that Adaptive-tile maximizes raw correspondence count. Fixed LoFTR produces many raw matches, but RANSAC removes most of them in these polar DOM cases. Adaptive-tile instead produces a smaller set of route-filtered matches and remains successful on all four representative cases.

For low-texture sparse/inconsistent pairs, Adaptive-tile retains geometrically usable matches in both regimes: 11 retained matches for the near-pole sparse case and 5 retained matches for the near-80S sparse case. These are both above the retained>=4 practical success threshold used in the benchmark.

The route behavior is also meaningful. Adaptive-tile does not blindly send every tile to a deep matcher. It skips invalid or unsuitable deep route candidates and falls back to persisted classic route results when those are the viable route. In the near-pole rich/inconsistent case, it exports only one viable SIFT+LightGlue deep tile and retains 8 RANSAC-consistent matches. In the near-80S rich/consistent case, it keeps the simpler SIFT+FLANN route across 9 valid tiles and retains 13 matches.

Deep manifest execution completed without failures for this rerun: LoFTR, SIFT+LightGlue, and SuperPoint+LightGlue each ran 4 manifests and 18 tasks; Adaptive-tile ran 1 grouped deep manifest and 1 task. Total deep tasks: 55 succeeded, 0 failed.
