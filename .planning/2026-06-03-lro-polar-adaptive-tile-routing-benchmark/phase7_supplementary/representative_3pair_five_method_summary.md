# Representative 3-Pair Five-Method Matching Summary

Output root: `/media/gengxun/My Passport/data/lro/testdata_lunar_80S_89.9S/texture_lighting_pair_selection/original_gsd/work/reduced-10m/lro_polar_adaptive_tile_routing_representative_3pair_20260604`

RANSAC summary: `ransac_match_visualization_summary.csv`; method-level summaries are under each method directory.

## Method Totals

| Method | Pre-ground input | Pre-ground retained | Pre-ground dropped | RANSAC input | RANSAC retained | RANSAC dropped | RANSAC retain % |
|---|---:|---:|---:|---:|---:|---:|---:|
| sift_flann | 4122 | 3843 | 279 | 3843 | 3816 | 27 | 99.3% |
| loftr | 25825 | 22561 | 3264 | 22561 | 15490 | 7071 | 68.7% |
| superpoint_lightglue | 5447 | 5121 | 326 | 5121 | 4326 | 795 | 84.5% |
| sift_lightglue | 6021 | 5908 | 113 | 5908 | 5567 | 341 | 94.2% |
| adaptive | 14928 | 14239 | 689 | 14239 | 14166 | 73 | 99.5% |

## Per-Pair Details

### near-80S / sparse-texture-lighting-stress
`REDUCED_M1137247155LE.echo.cal__REDUCED_M1200848465RE.echo.cal`

| Method | Pre-ground input -> retained | RANSAC input -> retained | RANSAC retain % |
|---|---:|---:|---:|
| sift_flann | 133 -> 83 | 83 -> 73 | 88.0% |
| loftr | 6099 -> 5663 | 5663 -> 5490 | 96.9% |
| superpoint_lightglue | 843 -> 841 | 841 -> 492 | 58.5% |
| sift_lightglue | 1361 -> 1361 | 1361 -> 1161 | 85.3% |
| adaptive | 349 -> 248 | 248 -> 231 | 93.1% |

### mid-latitude-selected / stable-overlap
`REDUCED_M140550700LE.echo.cal__REDUCED_M140537125RE.echo.cal`

| Method | Pre-ground input -> retained | RANSAC input -> retained | RANSAC retain % |
|---|---:|---:|---:|
| sift_flann | 2491 -> 2443 | 2443 -> 2438 | 99.8% |
| loftr | 12092 -> 11706 | 11706 -> 5019 | 42.9% |
| superpoint_lightglue | 3872 -> 3870 | 3870 -> 3592 | 92.8% |
| sift_lightglue | 2518 -> 2518 | 2518 -> 2456 | 97.5% |
| adaptive | 10552 -> 10440 | 10440 -> 10423 | 99.8% |

### high-polar-selected / difficult-texture
`REDUCED_M110860982RE.echo.cal__REDUCED_M110881352RE.echo.cal`

| Method | Pre-ground input -> retained | RANSAC input -> retained | RANSAC retain % |
|---|---:|---:|---:|
| sift_flann | 1498 -> 1317 | 1317 -> 1305 | 99.1% |
| loftr | 7634 -> 5192 | 5192 -> 4981 | 95.9% |
| superpoint_lightglue | 732 -> 410 | 410 -> 242 | 59.0% |
| sift_lightglue | 2142 -> 2029 | 2029 -> 1950 | 96.1% |
| adaptive | 4027 -> 3551 | 3551 -> 3512 | 98.9% |
